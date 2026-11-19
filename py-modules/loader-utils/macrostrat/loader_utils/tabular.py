"""Load one CSV into a table, inferring its structure.

The tabular counterpart to `load_layer`: the file is read with Polars, its
column types inferred, and its rows streamed in with `COPY`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import IO, Optional, Union

import polars as pl
from sqlalchemy.engine import Engine

from .tables import (
    LoadError,
    check_target,
    comment_original_names,
    copy_dataframe,
    create_table,
    dedupe,
    identifier,
    pg_type,
)


@dataclass
class LoadedTable:
    """What a CSV load created, or would create on a dry run."""

    schema: str
    table: str
    columns: list[str]
    types: list[str]
    rows: int
    # None on a dry run
    copied: Optional[int] = None


def load_csv(
    engine: Optional[Engine],
    source: Union[Path, str, IO[bytes]],
    *,
    schema: str = "temp",
    table: Optional[str] = None,
    replace: bool = False,
    append: bool = False,
    separator: str = ",",
    infer_rows: int = 0,
    null_values: Optional[list[str]] = None,
    all_text: bool = False,
    dry_run: bool = False,
) -> LoadedTable:
    """Load a CSV into `schema.table`, creating the table to match.

    `table` defaults to the file name, and is required for a stream, which must
    be seekable. `infer_rows` of 0 scans the whole file for types; `all_text`
    skips inference. A dry run reads the file and needs no engine.

    Each statement runs and commits on its own connection, so a caller whose open
    transaction has read `table` must commit first, or a replace will wait on it.
    """
    if replace and append:
        raise LoadError("replace and append are mutually exclusive")
    if isinstance(source, (str, Path)):
        source = Path(source)
        if not source.exists():
            raise LoadError(f"File {source} does not exist")
        if table is None:
            # Strip every suffix, so 'foo.csv.gz' becomes 'foo'
            table = identifier(source.name.split(".")[0], fallback="table")
    elif table is None:
        raise LoadError("A table name is required to load from a stream")

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

    result = LoadedTable(
        schema=schema,
        table=table,
        columns=columns,
        types=[pg_type(dtype) for dtype in df.schema.values()],
        rows=df.height,
    )
    if dry_run:
        return result

    check_target(engine, schema, table, replace=replace, append=append)

    if not append:
        create_table(engine, schema, table, columns, result.types, replace=replace)
        comment_original_names(engine, schema, table, original_columns, columns)

    result.copied = copy_dataframe(engine, df, schema, table, columns)
    return result


def _read_header(source: Union[Path, IO[bytes]], separator: str) -> list[str]:
    """Read just the header row of a CSV, leaving the source re-readable"""
    frame = pl.read_csv(
        source,
        separator=separator,
        has_header=False,
        n_rows=1,
        infer_schema=False,
    )
    if not isinstance(source, Path):
        source.seek(0)
    return list(frame.row(0))
