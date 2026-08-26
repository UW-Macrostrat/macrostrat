"""Shared machinery for the [cyan]load-csv[/] and [cyan]load-geo[/] commands.

Both commands work the same way: infer a table structure from a file, create it
(by default in the [cyan]temp[/] schema, named after the file), and stream the
data in with [cyan]COPY[/]. Everything they have in common lives here so the two
cannot drift apart.
"""

import re
from typing import Optional

import polars as pl
import typer
from psycopg.sql import SQL, Composed, Identifier, Literal
from rich import print
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from macrostrat.database.utils import run_sql
from macrostrat.utils import get_logger

log = get_logger(__name__)

COPY_BATCH_SIZE = 10_000

# Polars dtype -> PostgreSQL column type. Order matters: the first matching
# entry wins, so more specific types come first.
_TYPE_MAP = [
    (pl.Boolean, "boolean"),
    (pl.Int8, "smallint"),
    (pl.Int16, "smallint"),
    (pl.Int32, "integer"),
    (pl.Int64, "bigint"),
    (pl.UInt8, "smallint"),
    (pl.UInt16, "integer"),
    (pl.UInt32, "bigint"),
    (pl.UInt64, "numeric"),
    (pl.Float32, "real"),
    (pl.Float64, "double precision"),
    (pl.Date, "date"),
    (pl.Time, "time"),
    (pl.Duration, "interval"),
    (pl.String, "text"),
    (pl.Null, "text"),
    (pl.Object, "text"),
]


def pg_type(dtype: pl.DataType) -> str:
    """Find the PostgreSQL type corresponding to a Polars dtype"""
    if isinstance(dtype, pl.Datetime):
        return "timestamptz" if dtype.time_zone is not None else "timestamp"
    if isinstance(dtype, pl.Decimal):
        return "numeric"
    if isinstance(dtype, (pl.List, pl.Array, pl.Struct)):
        return "jsonb"
    for pl_type, pg_type_ in _TYPE_MAP:
        if dtype == pl_type:
            return pg_type_
    log.warning("No type mapping for %s; falling back to text", dtype)
    return "text"


def polars_from_pandas(df) -> pl.DataFrame:
    """Convert a pandas DataFrame to Polars without requiring pyarrow.

    `pl.from_pandas` needs pyarrow for anything that is not a plain numpy
    column, which is a heavy dependency to take on for a handoff. Converting
    column by column also lets us fix two pandas-isms on the way through:
    extension dtypes carry `pd.NA` (which Polars rejects), and missing floats
    arrive as `NaN` (which Postgres would store as a literal NaN rather than
    NULL).
    """
    return pl.DataFrame([_to_series(name, df[name]) for name in df.columns])


def _to_series(name: str, series) -> pl.Series:
    import pandas as pd

    def _as_objects() -> pl.Series:
        # Route pd.NA/NaT/NaN through None so Polars infers a nullable dtype
        values = series.astype(object).where(series.notna(), None)
        return pl.Series(name, values.tolist())

    if isinstance(series.dtype, pd.api.extensions.ExtensionDtype):
        return _as_objects()

    try:
        out = pl.Series(name, series.to_numpy())
    except (TypeError, ValueError):
        return _as_objects()

    if out.dtype in (pl.Float32, pl.Float64):
        # pandas uses NaN for missing numbers; Postgres wants NULL
        out = out.fill_nan(None)
    if out.dtype == pl.Object:
        # An all-null object column comes back as Object; let Polars re-infer
        return _as_objects()
    return out


def identifier(name: str, *, fallback: str = "column") -> str:
    """Coerce an arbitrary string into a reasonable unquoted-safe identifier"""
    name = name.strip()
    # Split camel-case boundaries before lowercasing, so 'IsPrimary' becomes
    # 'is_primary' rather than 'isprimary'
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name.lower())
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        return fallback
    if name[0].isdigit():
        name = f"{fallback}_{name}"
    # Postgres truncates identifiers at 63 bytes; do it ourselves so the
    # deduplication below stays meaningful.
    return name[:63]


def dedupe(names: list[str]) -> list[str]:
    """Disambiguate repeated identifiers by appending a counter"""
    counts: dict[str, int] = {}
    out = []
    for name in names:
        counts[name] = counts.get(name, 0) + 1
        if counts[name] > 1:
            name = f"{name}_{counts[name]}"
        out.append(name)
    return out


def table_exists(engine: Engine, schema: str, table: str) -> bool:
    with engine.connect() as conn:
        return inspect(conn).has_table(table, schema=schema)


def check_target(
    engine: Engine, schema: str, table: str, *, replace: bool, append: bool
):
    """Fail early and legibly when the destination is not what the caller expects"""
    exists = table_exists(engine, schema, table)
    if append and not exists:
        raise typer.BadParameter(
            f"Table {schema}.{table} does not exist; drop --append to create it"
        )
    if exists and not (append or replace):
        raise typer.BadParameter(
            f"Table {schema}.{table} already exists; "
            "pass --replace to overwrite it or --append to add to it"
        )


def column_defs(columns: list[str], types: list[str], *, sep: str = ", ") -> Composed:
    """Build the column-definition list for a CREATE TABLE statement"""
    return SQL(sep).join(
        SQL("{name} {type}").format(name=Identifier(name), type=SQL(type_))
        for name, type_ in zip(columns, types)
    )


def create_table(
    engine: Engine,
    schema: str,
    table: str,
    columns: list[str],
    types: list[str],
    *,
    replace: bool = False,
):
    run_sql(
        engine,
        "CREATE SCHEMA IF NOT EXISTS {schema}",
        dict(schema=Identifier(schema)),
        raise_errors=True,
    )
    if replace:
        run_sql(
            engine,
            "DROP TABLE IF EXISTS {table}",
            dict(table=Identifier(schema, table)),
            raise_errors=True,
        )
    run_sql(
        engine,
        "CREATE TABLE {table} ({columns})",
        dict(
            table=Identifier(schema, table),
            columns=column_defs(columns, types),
        ),
        raise_errors=True,
    )


def comment_original_names(
    engine: Engine,
    schema: str,
    table: str,
    original: list[str],
    columns: list[str],
):
    """Record the source column name wherever we had to mangle it.

    COMMENT does not accept a bind parameter, so the text has to be inlined as
    a quoted literal.
    """
    for source_name, name in zip(original, columns):
        if source_name == name:
            continue
        run_sql(
            engine,
            "COMMENT ON COLUMN {column} IS {comment}",
            dict(
                column=Identifier(schema, table, name),
                comment=Literal(source_name),
            ),
            raise_errors=True,
        )


def render_ddl(
    engine: Engine, schema: str, table: str, columns: list[str], types: list[str]
) -> str:
    stmt = SQL("CREATE TABLE {table} (\n  {columns}\n)").format(
        table=Identifier(schema, table),
        columns=column_defs(columns, types, sep=",\n  "),
    )
    with engine.connect() as conn:
        return stmt.as_string(conn.connection.driver_connection)


def copy_dataframe(
    engine: Engine,
    df: pl.DataFrame,
    schema: str,
    table: str,
    columns: Optional[list[str]] = None,
) -> int:
    """Stream a Polars dataframe into a table using COPY ... FROM STDIN"""
    columns = columns or df.columns
    stmt = SQL("COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv, NULL '')").format(
        table=Identifier(schema, table),
        columns=SQL(", ").join(Identifier(c) for c in columns),
    )

    # Drive the DBAPI connection directly: a raw cursor used inside a SQLAlchemy
    # Connection is invisible to its transaction bookkeeping, so the COPY gets
    # rolled back when the Connection closes.
    raw = engine.raw_connection()
    try:
        with raw.driver_connection.cursor() as cur:
            with cur.copy(stmt) as copy:
                # Polars writes NULL as an empty field, which round-trips
                # through the `NULL ''` above.
                for batch in df.iter_slices(COPY_BATCH_SIZE):
                    copy.write(batch.write_csv(include_header=False))
            n = cur.rowcount
        raw.commit()
    finally:
        raw.close()
    return n
