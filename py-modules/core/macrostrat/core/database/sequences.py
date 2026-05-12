import re
from dataclasses import dataclass

from psycopg.sql import Identifier
from rich import print

from macrostrat.database import Database

# TODO: incorporate this into the macrostrat.database module


@dataclass
class ResetSequenceResult:
    table: str
    column: str
    sequence: str
    new_value: int


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


def reset_sequence(
    db: Database,
    table: str,
    column: str | None = None,
    *,
    schema: str | None = None,
    start_val: int = None,
) -> ResetSequenceResult:
    """Helper to reset primary key or identity sequences for a given table. This can help ensure
    that primary key values can be generated correctly."""

    # separate table and schema name
    if schema is None:
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

    sql = "SELECT setval(:sequence_name, COALESCE(:start_val, (SELECT MAX({col_name})+1 FROM {table_name}), 1), false)"
    res = db.run_query(
        sql,
        dict(
            sequence_name=sequence_name,
            table_name=table_name,
            col_name=col_name,
            start_val=start_val,
        ),
    ).scalar()

    return ResetSequenceResult(
        table=full_table_name, column=_col_name, sequence=sequence_name, new_value=res
    )
