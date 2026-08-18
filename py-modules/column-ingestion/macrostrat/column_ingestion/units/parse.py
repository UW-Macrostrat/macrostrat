from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import polars as pl

from macrostrat.utils import get_logger

from ..environs import Environ, EnvironsProcessor
from ..intervals import (
    Interval,
    RelativeAge,
    get_interval_by_id,
    get_interval_from_text,
    get_intervals,
)
from ..lithologies import LithAbundance, Lithology, LithsProcessor


@dataclass
class Unit:
    id: int = -1
    col_id: int = -1
    #: Database `sections.id`, assigned once the section has been reconciled.
    section_id: int = -1
    #: The workbook's own section identifier, which groups units into sections before any
    #: database id exists. Kept apart from `section_id` so the mapping from workbook
    #: section to database section stays explicit rather than being overwritten in place.
    section_key: Any = None
    b_pos: float | None = None
    t_pos: float | None = None
    lithology: set[Lithology] = field(default_factory=set)
    environment: set[Environ] = field(default_factory=set)
    description: str | None = None
    #: Free-text remarks, kept apart from `description` because `unit_notes` composes the
    #: two into one note rather than storing either verbatim.
    comments: str | None = None
    name: str | None = None
    color: str | None = None

    # Relative age positioning
    b_age: RelativeAge | None = None
    t_age: RelativeAge | None = None


log = get_logger(__name__)


def rename_aliases(df, aliases):
    """Rename or alias columns in a data frame"""
    warnings = set()
    for old_name, new_name in aliases.items():
        if old_name in df.columns:
            if new_name not in df.columns:
                df = df.rename({old_name: new_name})
            else:
                warnings.add(
                    f"Both '{old_name}' and '{new_name}' are present in the data frame."
                )
    return df, warnings


class PositionAxisType(str, Enum):
    HEIGHT = "height"
    DEPTH = "depth"
    ORDINAL = "ordinal"


def get_units(db, data_file, **kwargs) -> {str: list[Unit]}:
    df = pl.read_excel(data_file, sheet_name="units")
    return get_units_from_df(db, df, **kwargs)


def get_units_from_df(
    db, df, *, position: PositionAxisType = PositionAxisType.HEIGHT, fill_values=False
) -> {str: list[Unit]}:
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

    # Split into groups by column_id
    groups = df.group_by(["col_id"])

    res = {}

    for (col_id,), group in groups:
        print(f"Column ID: {col_id}")
        # Set section_id to 1 if not present, or if all values are null
        if "section_id" not in group.columns or group["section_id"].is_null().all():
            group = group.with_columns(pl.lit(1).alias("section_id"))

        units = prepare_column_units(
            db, group, position=position, fill_values=fill_values
        )
        res[str(col_id)] = units
    return res


def prepare_column_units(db, df, **kwargs) -> list[Unit]:
    # Group by section_id
    sections = df.group_by(["section_id"])
    units = []
    for (section_id,), group in sections:
        print(f"Section ID: {section_id}")
        units.extend(prepare_section_units(db, group, **kwargs))
    return units


def prepare_section_units(
    db,
    df,
    *,
    position: PositionAxisType = PositionAxisType.HEIGHT,
    fill_values: bool = True,
) -> list[Unit]:
    # Sort by b_pos (descending if height)
    # TODO: figure out how to switch conventions for depth
    df = df.sort("b_pos", descending=True)

    # Fill in t_pos with the next b_pos value, unless it already exists
    # Do the same for intervals and proportions
    for suffix in ["pos", "prop", "int"]:
        b_col = "b_" + suffix
        t_col = "t_" + suffix
        # If the t_pos column does not exist, create it (empty for now)

        for col in [b_col, t_col]:
            if col in df.columns:
                continue
            df = df.with_columns(pl.lit(None, float).alias(col))

        # Create a column with default values for the top position of each unit
        _t_col = df[b_col].shift(1)

        if position == PositionAxisType.ORDINAL and t_col == "t_pos":
            # If ordinal, set the top position to the bottom position + 1 where it is unset
            _t_col = pl.when(_t_col.is_null()).then(df[b_col] + 1).otherwise(_t_col)

        df = df.with_columns(
            pl.when(pl.col(t_col).is_null())
            .then(_t_col)
            .otherwise(pl.col(t_col))
            .alias(t_col)
        )

    n_rows = df.shape[0]

    # Remove any rows where t_pos or b_pos is null
    df = df.filter((df["t_pos"].is_not_null()) & (df["b_pos"].is_not_null()))

    n_rows_2 = df.shape[0]

    # Allow for one null at the top and one at the bottom
    assert n_rows_2 >= (n_rows - 2)

    fill_specs = [
        "lithology",
        "minor_lith",
        "color",
        "grainsize",
        "strat_name",
        "facies",
        "name",
    ]
    for spec in fill_specs:
        if not fill_values:
            continue
        if spec not in df.columns:
            continue
        new_col = df[spec].fill_null(strategy="forward").alias(spec)
        # Cast the new column to a string
        new_col = new_col.cast(pl.Utf8)
        df = df.with_columns(new_col)
        # Fill 'none' values in the new column with nulls
        df = df.with_columns(
            pl.when(pl.col(spec) == "none")
            .then(pl.lit(None))
            .otherwise(pl.col(spec))
            .alias(spec)
        )

    # Get unique lithologies in the column
    for col in ["lithology", "minor_lith", "strat_name"]:
        if col not in df.columns:
            continue
        lithologies = df[col].unique().to_list()
        if len(lithologies) > 0:
            print_list(col, lithologies)

    res = []
    liths_processor = LithsProcessor(db)
    environs_processor = EnvironsProcessor(db)
    for row in df.iter_rows(named=True):
        lith = row.get("lithology")
        liths = liths_processor(lith, LithAbundance.DOMINANT)
        # Process minor lithologies if they are present
        liths |= liths_processor(row.get("minor_lith"), LithAbundance.SUBSIDIARY)

        unit = Unit(
            section_key=row.get("section_id"),
            environment=environs_processor(row.get("environment")),
            comments=row.get("comments"),
            b_pos=row["b_pos"],
            t_pos=row["t_pos"],
            description=row.get("description"),
            name=row.get("name"),
            lithology=liths,
            color=row.get("color"),
        )

        # Only relative age positioning is supported for now
        b_int = get_interval_from_text(db, row.get("b_int"))
        if b_int is not None:
            unit.b_age = RelativeAge(
                interval=b_int, proportion=coalesce(row.get("b_prop"), 0)
            )

        t_int = get_interval_from_text(db, row.get("t_int"))
        if t_int is not None:
            unit.t_age = RelativeAge(
                interval=t_int, proportion=coalesce(row.get("t_prop"), 1)
            )

        res.append(unit)

    return res


def coalesce(value, default):
    if value is None:
        return default
    return value


def print_list(title, lst):
    print(f"{title}:")
    for item in lst:
        print(f"  {item}")
