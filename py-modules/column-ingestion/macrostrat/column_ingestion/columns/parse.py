"""Columns and their sections, read out of a workbook.

Two sheets feed this: `columns` gives the `Column` objects, and `units` gives each
column's sections of units — the sheet's `col_id` / `section_id` pair is the column
structure, and the rows within a section are handed to `units.parse` to become `Unit`s.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from macrostrat.utils import get_logger

from ..refs import parse_ref_ids
from ..units.parse import (
    PositionAxisType,
    Unit,
    prepare_section_units,
    rename_aliases,
)
from .sections import Section, single_section

log = get_logger(__name__)


@dataclass
class Column:
    id: int = -1
    group_id: int = -1
    local_id: str | None = None
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    status_code: str = "in process"
    col_type: str = "column"
    #: A point location, used when no polygon is supplied. `geometry.resolve_geometry`
    #: treats a polygon as authoritative when both are present.
    lat: float | None = None
    lng: float | None = None
    geom: str | None = None
    rgeom: str | None = None
    #: The identifier this column carries in the dataset it came from, written to
    #: `macrostrat.cols.orig_id` and preferred over `(project_id, col_group_id, col_name)`
    #: when reconciling — see `columns.writer.column_identity`. `None` for workbook
    #: columns. Distinct from `local_id`, which is a workbook-local label used to attach
    #: units and references during one run and is not stored.
    orig_id: str | None = None
    #: Workbook-local `ref_id`s this column cites, resolved to `refs.id` by `refs`.
    ref_ids: list[str] = field(default_factory=list)
    #: The column's sections, each holding its units. Every unit belongs to exactly one
    #: section. **The norm is one section per column**: assign `units` and that is what
    #: you get. Set `sections` directly only when told otherwise — a source that owns its
    #: sections (`Section(orig_id=...)`), or an explicit `sections.split_at_gaps`.
    sections: list[Section] = field(default_factory=list)

    @property
    def units(self) -> list[Unit]:
        """Every unit in the column, section by section."""
        return [unit for section in self.sections for unit in section.units]

    @units.setter
    def units(self, units: list[Unit]):
        """One section holding `units` — the default division of a column."""
        self.sections = single_section(units)


def _as_float(value) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_column_data(data_file, meta) -> list[Column]:
    df = pl.read_excel(data_file, sheet_name="columns")

    df = df.rename(
        {
            "name": "col_name",
            "id": "col_id",
            "type": "col_type",
        },
        strict=False,
    )

    print(df.head())

    columns = []
    for row in df.iter_rows(named=True):
        geom = row.get("rgeom", getattr(meta, "rgeom", None))

        col = Column(
            # TODO: implement ID upgrading to handle existing columns
            local_id=str(row.get("col_id")),
            name=row.get("col_name"),
            description=row.get("description"),
            status_code=row.get(
                "status_code", getattr(meta, "status_code", "in process")
            ),
            col_type=row.get("col_type", getattr(meta, "col_type", "column")),
            lat=_as_float(row.get("lat")),
            lng=_as_float(row.get("lng")),
            ref_ids=parse_ref_ids(row.get("ref_ids")),
            geom=row.get("geom"),
            rgeom=geom,
        )
        columns.append(col)
    return columns


def get_sections(db, data_file, **kwargs) -> dict[str, list[Section]]:
    """The `units` sheet as each column's sections, keyed by the workbook's column id."""
    df = pl.read_excel(data_file, sheet_name="units")
    return get_sections_from_df(db, df, **kwargs)


def get_sections_from_df(
    db, df, *, position: PositionAxisType = PositionAxisType.HEIGHT, fill_values=False
) -> dict[str, list[Section]]:
    """Group the units sheet into columns and sections, and parse each section's units.

    A `section_id` the author bothered to write is the section's identifier, exactly as a
    source dataset's would be: it becomes `Section.orig_id`, and renumbering the sheet
    changes which sections exist. A column with no labels is one section.
    """
    # Rename some columns
    df, warnings = rename_aliases(
        df,
        {
            "pos": "position",
            "position": "b_pos",
            "bottom_position": "b_pos",
            "height": "b_pos",
            "column": "col_id",
            "column_id": "col_id",
            "unit_name": "name",
            # The workbook calls it `unit_description`; `unit_notes` composes it with
            # `comments` rather than storing either verbatim.
            "unit_description": "description",
        },
    )

    for warning in warnings:
        log.warning(warning)

    # Ensure that either b_pos or t_pos is present
    if "b_pos" not in df.columns and "t_pos" not in df.columns:
        raise ValueError("Either b_pos or t_pos must be present in the data frame.")

    # Create the columns that don't exist
    for col in ["b_pos", "t_pos"]:
        if col not in df.columns:
            newcol = pl.lit(None).alias(col)
        else:
            newcol = pl.col(col).cast(pl.Float64, strict=False)
        df = df.with_columns(newcol)

    res = {}
    for (col_id,), column_rows in df.group_by(["col_id"]):
        print(f"Column ID: {col_id}")
        if (
            "section_id" not in column_rows.columns
            or column_rows["section_id"].is_null().all()
        ):
            units = prepare_section_units(
                db, column_rows, position=position, fill_values=fill_values
            )
            res[str(col_id)] = single_section(units)
            continue

        sections = []
        for (section_id,), section_rows in column_rows.group_by(["section_id"]):
            print(f"Section ID: {section_id}")
            units = prepare_section_units(
                db, section_rows, position=position, fill_values=fill_values
            )
            sections.append(Section(orig_id=section_id, units=units))
        res[str(col_id)] = sections
    return res
