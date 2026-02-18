from dataclasses import dataclass, field

import polars as pl

from .lithologies import Lithology, process_liths_text


@dataclass
class Unit:
    id: int = -1
    col_id: int = -1
    section_id: str | None = None
    b_pos: float | None = None
    t_pos: float | None = None
    lithology: set[Lithology] = field(default_factory=set)
    description: str | None = None
    name: str | None = None
    color: str | None = None


def get_units(data_file) -> {str: list[Unit]}:
    df = pl.read_excel(data_file, sheet_name="units")

    # Rename some columns
    df = df.rename(
        {
            "position": "b_pos",
            "bottom_position": "b_pos",
            "height": "b_pos",
            "column": "col_id",
            "column_id": "col_id",
        },
        strict=False,
    )

    # Ensure b_pos is numeric
    df = df.with_columns(pl.col("b_pos").cast(pl.Float64, strict=False))

    # Split into groups by column_id
    groups = df.group_by(["col_id"])

    res = {}

    for (col_id,), group in groups:
        print(f"Column ID: {col_id}")
        units = prepare_column_units(group)
        res[str(col_id)] = units
    return res


def prepare_column_units(df) -> list[Unit]:
    # Sort by b_pos (descending if height)
    df = df.sort("b_pos", descending=True)
    # If the t_pos column does not exist, create it (empty for now)
    if "t_pos" not in df.columns:
        df = df.with_columns(pl.lit(None, float).alias("t_pos"))

    # Create a column with default values for the top position of each unit
    t_col = df["b_pos"].shift(1)

    # Fill in t_pos with the next b_pos value, unless it already exists
    df = df.with_columns(
        pl.when(pl.col("t_pos").is_null())
        .then(t_col)
        .otherwise(pl.col("t_pos"))
        .alias("t_pos")
    )

    n_rows = df.shape[0]

    # Remove any rows where t_pos or b_pos is null
    df = df.filter((df["t_pos"].is_not_null()) & (df["b_pos"].is_not_null()))

    n_rows_2 = df.shape[0]

    # Allow for one null at the top and one at the bottom
    assert n_rows_2 >= (n_rows - 2)

    fill_specs = ["lithology", "color", "grainsize", "strat_name", "facies"]
    cols = [
        pl.col(spec).fill_null(strategy="backward").alias(spec)
        for spec in fill_specs
        if spec in df.columns
    ]

    # Fill lithology info upwards
    df = df.with_columns(*cols)

    # Get unique lithologies in the column
    lithologies = df["lithology"].unique().to_list()
    print_list("Lithologies", lithologies)

    # Get strat names
    strat_names = df["strat_name"].unique().to_list()
    print_list("Strat_names", strat_names)

    res = []
    for row in df.iter_rows(named=True):
        lith = row.get("lithology")
        liths = set()
        if lith is not None:
            liths = process_liths_text(lith)

        unit = Unit(
            section_id=row.get("section_id"),
            b_pos=row["b_pos"],
            t_pos=row["t_pos"],
            description=row.get("description"),
            name=row.get("name"),
            lithology=liths,
            color=row.get("color"),
        )
        print(unit)
        res.append(unit)
    return res


def print_list(title, lst):
    print(f"{title}:")
    for item in lst:
        print(f"  {item}")
