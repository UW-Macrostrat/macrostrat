"""Columns and their sections, read out of a workbook.

Two sheets feed this: `columns` gives the `Column` objects, and `units` gives each
column's sections of units — the sheet's `col_id` / `section_id` pair is the column
structure, and the rows within a section are handed to `units.parse` to become `Unit`s.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from macrostrat.utils import get_logger

from .. import notices
from ..metadata import parse_axis_type, parse_fill_values
from ..refs import parse_ref_ids
from ..units.parse import (
    ROW_COLUMN,
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
    #: Which way positions run: `height`, `depth` or `age` (the workbook's `axis_type`).
    axis_type: str | None = None
    #: Whether blank descriptive cells are filled along the axis (`fill_values`).
    fill_values: bool = False
    #: A point location, used when no polygon is supplied. `column_utils.resolve_geometry`
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


def _as_float(value, column: str | None = None) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        if column is not None:
            notices.warning(
                "unreadable-number",
                f"`{column}` is not a number: {value!r}",
                column=column,
            )
        return None


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coalesce(*values):
    for value in values:
        if value is not None and not (isinstance(value, str) and not value.strip()):
            return value
    return None


def get_column_data(data_file, meta) -> list[Column]:
    return columns_from_df(pl.read_excel(data_file, sheet_name="columns"), meta)


def columns_from_df(df, meta) -> list[Column]:
    """The `columns` sheet as `Column` objects. Defaults come from the metadata."""
    df = df.rename(
        {
            "name": "col_name",
            "id": "col_id",
            "type": "col_type",
        },
        strict=False,
    )

    columns = []
    seen: set[str] = set()
    for number, row in enumerate(df.iter_rows(named=True), start=2):
        local_id = _text(row.get("col_id"))
        with notices.notice_context(sheet="columns", row=number, col_id=local_id):
            if local_id is None:
                if len(df) == 1:
                    local_id = "1"
                else:
                    notices.error("column-missing-id", "A column needs a `col_id`")
                    continue
            if local_id in seen:
                notices.error("column-duplicate-id", f"Duplicate col_id {local_id!r}")
                continue
            seen.add(local_id)
            name = _text(row.get("col_name"))
            if name is None:
                notices.error("column-missing-name", "A column needs a `col_name`")
                name = f"Column {local_id}"

            col = Column(
                # TODO: implement ID upgrading to handle existing columns
                local_id=local_id,
                name=name,
                description=_text(row.get("description")),
                status_code=_coalesce(
                    row.get("status_code"), getattr(meta, "status_code", None)
                )
                or "in process",
                col_type=_coalesce(row.get("col_type"), getattr(meta, "col_type", None))
                or "column",
                axis_type=_coalesce(
                    parse_axis_type(row.get("axis_type")),
                    getattr(meta, "axis_type", None),
                ),
                fill_values=_coalesce(
                    parse_fill_values(row.get("fill_values")),
                    getattr(meta, "fill_values", False),
                ),
                lat=_as_float(row.get("lat"), "lat"),
                lng=_as_float(row.get("lng"), "lng"),
                ref_ids=parse_ref_ids(row.get("ref_ids")),
                geom=_text(row.get("geom")),
                rgeom=_text(_coalesce(row.get("rgeom"), getattr(meta, "rgeom", None))),
            )
            columns.append(col)
    return columns


def get_sections(db, data_file, **kwargs) -> dict[str, list[Section]]:
    """The `units` sheet as each column's sections, keyed by the workbook's column id."""
    df = pl.read_excel(data_file, sheet_name="units")
    return get_sections_from_df(db, df, **kwargs)


#: Header synonyms on the units sheet, as the format specification's *Field aliases* lists them.
UNIT_FIELD_ALIASES = {
    "pos": "position",
    "height": "position",
    "depth": "position",
    "b_position": "b_pos",
    "bottom_position": "b_pos",
    "base_position": "b_pos",
    "position_bottom": "b_pos",
    "bottom": "b_pos",
    "base": "b_pos",
    "bottom_height": "b_pos",
    "base_height": "b_pos",
    "bottom_depth": "b_pos",
    "base_depth": "b_pos",
    "t_position": "t_pos",
    "top_position": "t_pos",
    "position_top": "t_pos",
    "top": "t_pos",
    "top_height": "t_pos",
    "top_depth": "t_pos",
    "column": "col_id",
    "column_id": "col_id",
    "unit_name": "name",
    # The workbook calls it `unit_description`; `unit_notes` composes it with
    # `comments` rather than storing either verbatim.
    "unit_description": "description",
}

#: Position headers named for an axis, and the axis they imply.
_AXIS_NAMED = {"height": PositionAxisType.HEIGHT, "depth": PositionAxisType.DEPTH}


def get_sections_from_df(
    db,
    df,
    *,
    position: PositionAxisType = PositionAxisType.HEIGHT,
    fill_values=False,
    column_settings: dict[str, tuple[PositionAxisType, bool]] | None = None,
    vocab=None,
) -> dict[str, list[Section]]:
    """Group the units sheet into columns and sections, and parse each section's units.

    `column_settings` gives a column's own axis and filling, keyed by workbook column
    id; `position` and `fill_values` apply to any column it does not name.

    A `section_id` the author bothered to write is the section's identifier, exactly as a
    source dataset's would be: it becomes `Section.orig_id`, and renumbering the sheet
    changes which sections exist. A column with no labels is one section.
    """
    default_position, default_fill = position, fill_values
    axis_named = [name for name in _AXIS_NAMED if name in df.columns]
    df, warnings = rename_aliases(df, UNIT_FIELD_ALIASES)

    for warning in warnings:
        notices.warning("ambiguous-columns", warning, sheet="units")

    if not {"position", "b_pos", "t_pos"} & set(df.columns):
        raise ValueError("The units sheet needs a `position`, `b_pos` or `t_pos`.")

    # Remember each row's place in the sheet (header is row 1) before sorting
    if ROW_COLUMN not in df.columns:
        df = df.with_row_index(ROW_COLUMN, offset=2)
    if "col_id" not in df.columns:
        # A single-column workbook may leave the column id out
        df = df.with_columns(pl.lit("1").alias("col_id"))
    if "section_id" in df.columns:
        df = df.with_columns(pl.col("section_id").cast(pl.Utf8, strict=False))

    # Create the columns that don't exist
    for col in ["b_pos", "t_pos"]:
        if col not in df.columns:
            newcol = pl.lit(None, pl.Float64).alias(col)
        else:
            newcol = pl.col(col).cast(pl.Float64, strict=False)
        df = df.with_columns(newcol)

    settings = column_settings or {}
    res = {}
    for (col_id,), column_rows in df.group_by(["col_id"], maintain_order=True):
        with notices.notice_context(sheet="units", col_id=str(col_id)):
            position, fill_values = settings.get(
                str(col_id), (default_position, default_fill)
            )
            _check_column_axis(position, fill_values, axis_named)
            if (
                "section_id" not in column_rows.columns
                or column_rows["section_id"].is_null().all()
            ):
                units = prepare_section_units(
                    db,
                    column_rows,
                    position=position,
                    fill_values=fill_values,
                    vocab=vocab,
                )
                res[str(col_id)] = single_section(units)
                continue

            sections = []
            for (section_id,), section_rows in column_rows.group_by(
                ["section_id"], maintain_order=True
            ):
                with notices.notice_context(section=section_id):
                    units = prepare_section_units(
                        db,
                        section_rows,
                        position=position,
                        fill_values=fill_values,
                        vocab=vocab,
                    )
                sections.append(Section(orig_id=section_id, units=units))
            res[str(col_id)] = sections
    return res


def _check_column_axis(position, fill_values, axis_named: list[str]) -> None:
    """Warn where a column's headers or settings contradict its axis."""
    for name in axis_named:
        if position == PositionAxisType.ORDINAL or _AXIS_NAMED[name] == position:
            continue
        notices.warning(
            "axis-name-mismatch",
            f"A `{name}` column on a {position.value} axis: check `axis_type`",
            column=name,
        )
    if fill_values and position == PositionAxisType.ORDINAL:
        notices.warning(
            "no-filling-on-age-axis",
            "fill_values is ignored on an age axis",
            column="fill_values",
        )
