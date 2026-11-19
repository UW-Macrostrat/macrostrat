"""Load CSV files into the database, inferring a table structure from the data.

This is a working-data convenience: it behaves more or less like [cyan]COPY[/],
except that the destination table is created to match the file's inferred
schema. Tables land in the [cyan]temp[/] schema by default.
"""

from io import BytesIO
from pathlib import Path
from sys import stderr, stdin
from typing import IO, Optional, Union

import typer
from rich import print
from sqlalchemy.engine import Engine
from typer import Argument, Option

from macrostrat.loader_utils import LoadError, load_csv, render_ddl
from macrostrat.utils import get_logger

from .utils import engine_for_db_name

log = get_logger(__name__)


def load_csv_command(
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
    source: Union[Path, IO[bytes]] = file
    label = str(file)
    if str(file) == "-":
        if table is None:
            raise typer.BadParameter("--table is required when reading from stdin")
        source = BytesIO(stdin.buffer.read())
        label = "<stdin>"

    try:
        result = load_csv(
            engine,
            source,
            schema=schema,
            table=table,
            replace=replace,
            append=append,
            separator=separator,
            infer_rows=infer_rows,
            null_values=null_values,
            all_text=all_text,
            dry_run=dry_run,
        )
    except LoadError as err:
        raise typer.BadParameter(str(err)) from err

    if dry_run:
        print(render_ddl(engine, schema, result.table, result.columns, result.types))
        return

    print(
        f"[dim]Loaded[/] [bold cyan]{label}[/] [dim]→[/] "
        f"[bold green]{schema}.{result.table}[/] "
        f"[dim]({result.rows} rows, {len(result.columns)} columns; "
        f"copied {result.copied})[/]",
        file=stderr,
    )
