"""Load CSV files into the database, inferring a table structure from the data.

This is a working-data convenience: it behaves more or less like [cyan]COPY[/],
except that the destination table is created to match the file's inferred
schema. Tables land in the [cyan]temp[/] schema by default.
"""

from io import BytesIO
from pathlib import Path
from sys import stderr, stdin
from typing import IO, Optional, Union

import polars as pl
import typer
from rich import print
from sqlalchemy.engine import Engine
from typer import Argument, Option

from macrostrat.utils import get_logger

from .load_utils import (
    check_target,
    comment_original_names,
    copy_dataframe,
    create_table,
    dedupe,
    identifier,
    pg_type,
    render_ddl,
)
from .utils import engine_for_db_name

log = get_logger(__name__)


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
            table = identifier(file.name.split(".")[0], fallback="table")

    # Read the header ourselves and hand polars the sanitized names. Left to its
    # own devices, polars renames duplicate headers to '<name>_duplicated_0',
    # which would then leak into the column names we generate.
    original_columns = _read_header(source, separator)
    columns = dedupe([identifier(c) for c in original_columns])

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

    types = [pg_type(dtype) for dtype in df.schema.values()]

    if dry_run:
        print(render_ddl(engine, schema, table, columns, types))
        return

    print(
        f"[dim]Loading[/] [bold cyan]{label}[/] [dim]→[/] "
        f"[bold green]{schema}.{table}[/] "
        f"[dim]({df.height} rows, {df.width} columns)[/]",
        file=stderr,
    )

    check_target(engine, schema, table, replace=replace, append=append)

    if not append:
        create_table(engine, schema, table, columns, types, replace=replace)
        comment_original_names(engine, schema, table, original_columns, columns)

    n = copy_dataframe(engine, df, schema, table, columns)
    print(f"[dim]Copied[/] [bold green]{n}[/] [dim]rows[/]", file=stderr)


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
