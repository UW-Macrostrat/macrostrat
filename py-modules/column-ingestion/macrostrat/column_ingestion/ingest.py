import polars as pl
from openpyxl import load_workbook


def ingest_columns_from_file(data_file):
    # Get sheet names
    workbook = load_workbook(data_file, read_only=True)
    sheet_names = workbook.sheetnames

    print(f"Sheets: {sheet_names}")

    if "units" not in sheet_names:
        raise ValueError("Sheet 'units' not found in the data file")

    df = pl.read_excel(data_file, sheet_name="units")
    print(df.head())

    # Rename some columns
    df = df.rename({
        "position": "b_pos",
        "bottom_position": "b_pos",
        "height": "b_pos",
        "column": "col_id",
        "column_id": "col_id",
    }, strict=False)

    # Ensure b_pos is numeric
    df = df.with_columns(
        pl.col("b_pos").cast(pl.Float64, strict=False)
    )

    # Split into groups by column_id
    groups = df.group_by(["col_id"])

    for (col_id,), group in groups:
        print(f"Column ID: {col_id}")
        print(group.head())

        prepare_column_units(col_id, group)


def prepare_column_units(col_id, df):
    # Sort by b_pos (descending if height)
    df = df.sort("b_pos", descending=True)
    # If the t_pos column does not exist, create it (empty for now)
    if "t_pos" not in df.columns:
        df = df.with_columns(
            pl.lit(None, float).alias("t_pos")
        )

    # Create a column with default values for the top position of each unit
    t_col = df["b_pos"].shift(1)

    # Fill in t_pos with the next b_pos value, unless it already exists
    df = df.with_columns(
       pl.when(pl.col("t_pos").is_null()).then(t_col).otherwise(pl.col("t_pos")).alias("t_pos")
    )

    n_rows = df.shape[0]

    # Remove any rows where t_pos or b_pos is null
    df = df.filter(
        (df["t_pos"].is_not_null()) & (df["b_pos"].is_not_null())
    )

    n_rows_2 = df.shape[0]

    # Allow for one null at the top and one at the bottom
    assert n_rows_2 >= (n_rows - 2)

    print(df.head())
