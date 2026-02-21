import re

from psycopg2.sql import Identifier
from rich import print

from macrostrat.database import Database


def is_autoincrementing_column(col):
    return (
        col.get("autoincrement") is True
        or col.get("identity") is not None
        or (col.get("default") and "nextval" in str(col["default"]))
    )


def sequence_name_for_column(col):
    if col.get("identity") is not None:
        return col["identity"]["sequence"]
    elif col.get("default") and "nextval" in str(col["default"]):
        # Extract the sequence name from the default value
        default = str(col["default"])

        match = re.search(r"nextval\('([^']+)'(::regclass)?\)", default)
        if match:
            return match.group(1)

    return None


def reset_sequences(db: Database, table: str, column: str | None = None):
    """Helper to reset primary key or identity sequences for a given table. This can help ensure
    that primary key values can be generated correctly."""

    # separate table and schema name
    schema = "public"
    if "." in table:
        schema, table = table.split(".", 1)

    insp = db.inspector
    if not insp.has_table(table, schema=schema):
        raise ValueError(f"Table {table} does not exist in schema {schema}")

    columns = insp.get_columns(table, schema=schema)

    # Find autoincrement columns
    increment_cols = [col for col in columns if is_autoincrementing_column(col)]
    if len(increment_cols) == 0:
        raise ValueError(f"No identity columns found in table {table}")

    if column is not None:
        increment_cols = [col for col in increment_cols if col["name"] == column]
        if len(increment_cols) == 0:
            raise ValueError(
                f"No identity column named {column} found in table {table}"
            )

    if len(increment_cols) > 1:
        columns = ", ".join(col["name"] for col in increment_cols)
        raise ValueError(
            f"Multiple identity columns found in table {table}, ({columns}). Please specify a column to fix.",
        )

    identity_col = increment_cols[0]
    sequence_name = sequence_name_for_column(identity_col)
    if sequence_name is None:
        raise ValueError(
            f"Could not determine sequence name for column {identity_col["name"]} in table {table}"
        )

    _col_name = identity_col["name"]
    col_name = Identifier(_col_name)
    table_name = Identifier(schema, table)

    full_table_name = f"{schema}.{table}" if schema else table

    sql = "SELECT setval(:sequence_name, COALESCE((SELECT MAX({col_name}) FROM {table_name}), 0) + 1, false)"
    res = db.run_query(
        sql,
        dict(sequence_name=sequence_name, table_name=table_name, col_name=col_name),
    ).scalar()

    print(f"table:     [bold]{full_table_name}[/]")
    print(f"column:    [bold]{_col_name}[/]")
    print(f"sequence:  [bold]{sequence_name}[/]")
    print(f"new value: [bold green]{res}[/]")
