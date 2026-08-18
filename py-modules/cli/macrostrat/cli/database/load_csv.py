"""Load CSV files into the database, inferring a table structure from the data.

This is a working-data convenience: it behaves more or less like [cyan]COPY[/],
except that the destination table is created to match the file's inferred
schema. Tables land in the [cyan]temp[/] schema by default.
"""

import re
from io import BytesIO
from pathlib import Path
from sys import stderr, stdin
from typing import IO, Optional, Union

import polars as pl
import typer
from psycopg.sql import SQL, Composed, Identifier, Literal
from rich import print
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from typer import Argument, Option

from macrostrat.database.utils import run_sql
from macrostrat.utils import get_logger

from .utils import engine_for_db_name

log = get_logger(__name__)

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
]

COPY_BATCH_SIZE = 10_000


def _pg_type(dtype: pl.DataType) -> str:
    """Find the PostgreSQL type corresponding to a Polars dtype"""
    if isinstance(dtype, pl.Datetime):
        return "timestamptz" if dtype.time_zone is not None else "timestamp"
    if isinstance(dtype, pl.Decimal):
        return "numeric"
    for pl_type, pg_type in _TYPE_MAP:
        if dtype == pl_type:
            return pg_type
    log.warning("No type mapping for %s; falling back to text", dtype)
    return "text"


def _identifier(name: str, *, fallback: str = "column") -> str:
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


def _dedupe(names: list[str]) -> list[str]:
    """Disambiguate repeated identifiers by appending a counter"""
    counts: dict[str, int] = {}
    out = []
    for name in names:
        counts[name] = counts.get(name, 0) + 1
        if counts[name] > 1:
            name = f"{name}_{counts[name]}"
        out.append(name)
    return out


def load_csv(
    files: list[Path] = Argument(
        ..., help="CSV file(s) to load. Use [cyan]-[/] to read from stdin."
    ),
    schema: str = Option("temp", "--schema", "-n", help="Schema to create tables in"),
    table: Optional[str] = Option(
        None,
        "--table",
        "-t",
        help="Table name (defaults to the file name). Only valid for a single file.",
    ),
    database: Optional[str] = Option(None, "--database", help="Database to connect to"),
    replace: bool = Option(
        False, "--replace", help="Drop and recreate the table if it already exists"
    ),
    append: bool = Option(
        False, "--append", help="Append to an existing table instead of creating it"
    ),
    separator: str = Option(",", "--separator", help="Field separator"),
    infer_rows: int = Option(
        0,
        "--infer-rows",
        help="Rows to scan for type inference (0 scans the whole file)",
    ),
    null_value: list[str] = Option(
        [], "--null", help="String(s) to treat as NULL (repeatable)"
    ),
    all_text: bool = Option(
        False, "--all-text", help="Skip type inference and create every column as text"
    ),
    dry_run: bool = Option(
        False,
        "--dry-run",
        help="Print the inferred table structure without touching the database",
    ),
):
    """Load CSV files into the database, creating tables to match the data.

    Like [cyan]COPY[/], but the destination table structure is inferred from the
    file rather than having to exist beforehand. Tables are named after their
    file and created in the [cyan]temp[/] schema by default.
    """
    if table is not None and len(files) > 1:
        raise typer.BadParameter("--table cannot be used with multiple files")
    if replace and append:
        raise typer.BadParameter("--replace and --append are mutually exclusive")

    engine = engine_for_db_name(database)

    for file in files:
        _load_one(
            engine,
            file,
            schema=schema,
            table=table,
            replace=replace,
            append=append,
            separator=separator,
            infer_rows=infer_rows,
            null_values=list(null_value) or None,
            all_text=all_text,
            dry_run=dry_run,
        )


def _load_one(
    engine: Engine,
    file: Path,
    *,
    schema: str,
    table: Optional[str],
    replace: bool = False,
    append: bool = False,
    separator: str = ",",
    infer_rows: int = 0,
    null_values: Optional[list[str]] = None,
    all_text: bool = False,
    dry_run: bool = False,
):
    if str(file) == "-":
        if table is None:
            raise typer.BadParameter("--table is required when reading from stdin")
        source: Union[Path, IO[bytes]] = BytesIO(stdin.buffer.read())
        label = "<stdin>"
    else:
        if not file.exists():
            raise typer.BadParameter(f"File {file} does not exist")
        source = file
        label = str(file)
        if table is None:
            # Strip every suffix, so 'foo.csv.gz' becomes 'foo'
            table = _identifier(file.name.split(".")[0], fallback="table")

    # Read the header ourselves and hand polars the sanitized names. Left to its
    # own devices, polars renames duplicate headers to '<name>_duplicated_0',
    # which would then leak into the column names we generate.
    original_columns = _read_header(source, separator)
    columns = _dedupe([_identifier(c) for c in original_columns])

    df = pl.read_csv(
        source,
        separator=separator,
        has_header=True,
        new_columns=columns,
        # None scans the entire file, which is what we want for working data: a
        # partial scan silently mistypes columns whose surprises come late.
        infer_schema_length=infer_rows or None,
        infer_schema=not all_text,
        null_values=null_values,
        try_parse_dates=not all_text,
    )

    types = [_pg_type(dtype) for dtype in df.schema.values()]

    if dry_run:
        print(_render_ddl(engine, schema, table, columns, types))
        return

    print(
        f"[dim]Loading[/] [bold cyan]{label}[/] [dim]→[/] "
        f"[bold green]{schema}.{table}[/] "
        f"[dim]({df.height} rows, {df.width} columns)[/]",
        file=stderr,
    )

    exists = _table_exists(engine, schema, table)
    if append and not exists:
        raise typer.BadParameter(
            f"Table {schema}.{table} does not exist; drop --append to create it"
        )
    if exists and not (append or replace):
        raise typer.BadParameter(
            f"Table {schema}.{table} already exists; "
            "pass --replace to overwrite it or --append to add to it"
        )

    if not append:
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
                columns=_column_defs(columns, types),
            ),
            raise_errors=True,
        )

        # Record the original header wherever we had to mangle it. COMMENT does
        # not accept a bind parameter, so the text has to be inlined as a
        # quoted literal.
        for original, name in zip(original_columns, columns):
            if original == name:
                continue
            run_sql(
                engine,
                "COMMENT ON COLUMN {column} IS {comment}",
                dict(
                    column=Identifier(schema, table, name),
                    comment=Literal(original),
                ),
                raise_errors=True,
            )

    n = _copy_dataframe(engine, df, schema, table, columns)
    print(f"[dim]Copied[/] [bold green]{n}[/] [dim]rows[/]", file=stderr)


def _table_exists(engine: Engine, schema: str, table: str) -> bool:
    with engine.connect() as conn:
        return inspect(conn).has_table(table, schema=schema)


def _read_header(source: Union[Path, IO[bytes]], separator: str) -> list[str]:
    """Read just the header row of a CSV, leaving the source re-readable"""
    frame = pl.read_csv(
        source,
        separator=separator,
        has_header=False,
        n_rows=1,
        infer_schema=False,
    )
    if isinstance(source, BytesIO):
        source.seek(0)
    return list(frame.row(0))


def _column_defs(columns: list[str], types: list[str]) -> Composed:
    """Build the column-definition list for a CREATE TABLE statement"""
    return SQL(", ").join(
        SQL("{name} {type}").format(name=Identifier(name), type=SQL(type_))
        for name, type_ in zip(columns, types)
    )


def _render_ddl(
    engine: Engine, schema: str, table: str, columns: list[str], types: list[str]
) -> str:
    stmt = SQL("CREATE TABLE {table} (\n  {columns}\n)").format(
        table=Identifier(schema, table),
        columns=SQL(",\n  ").join(
            SQL("{name} {type}").format(name=Identifier(name), type=SQL(type_))
            for name, type_ in zip(columns, types)
        ),
    )
    with engine.connect() as conn:
        return stmt.as_string(conn.connection.driver_connection)


def _copy_dataframe(
    engine: Engine, df: pl.DataFrame, schema: str, table: str, columns: list[str]
) -> int:
    """Stream a dataframe into a table using COPY ... FROM STDIN"""
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
