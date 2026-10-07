"""VACUUM tables one at a time, measuring the space each gives back."""

import time
from dataclasses import dataclass
from typing import Iterable, Iterator

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

_size = text("SELECT pg_total_relation_size(CAST(:table AS regclass))")

# Partitioned parents are left out: their partitions are listed on their own.
_all_tables = """
SELECT quote_ident(n.nspname) || '.' || quote_ident(c.relname) AS name
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'm')
  AND c.relpersistence <> 't'
  AND n.nspname NOT IN ('information_schema', 'pg_toast')
"""


@dataclass
class VacuumResult:
    table: str
    before: int
    after: int
    seconds: float
    error: str | None = None

    @property
    def saved(self) -> int:
        return self.before - self.after


def list_tables(engine: Engine, schema: str | None = None) -> list[str]:
    """Every vacuumable table, largest first."""
    sql = _all_tables
    params = {}
    if schema is not None:
        sql += "  AND n.nspname = :schema\n"
        params["schema"] = schema
    sql += "ORDER BY pg_total_relation_size(c.oid) DESC"
    with engine.connect() as conn:
        return list(conn.execute(text(sql), params).scalars())


def resolve_tables(engine: Engine, tables: Iterable[str]) -> list[str]:
    """Canonical, quoted names for user-given tables; raises if one is missing."""
    with engine.connect() as conn:
        return [
            conn.execute(
                text("SELECT CAST(CAST(:table AS regclass) AS text)"), dict(table=t)
            ).scalar()
            for t in tables
        ]


def database_size(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT pg_database_size(current_database())")
        ).scalar()


def vacuum_tables(
    engine: Engine, tables: Iterable[str], *, full: bool = False
) -> Iterator[VacuumResult]:
    """VACUUM (ANALYZE) each table, yielding its size before and after.

    Plain VACUUM marks dead rows reusable but rarely shrinks files; `full`
    rewrites each table compactly, holding an exclusive lock and needing free
    disk space for the new copy while it runs.
    """
    options = "ANALYZE, SKIP_LOCKED"
    if full:
        # A sweep can pass over a locked table; a named rewrite should wait for it.
        options = "FULL, ANALYZE"
    # VACUUM cannot run inside a transaction block.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for table in tables:
            t0 = time.time()
            try:
                before = conn.execute(_size, dict(table=table)).scalar()
                conn.exec_driver_sql(f"VACUUM ({options}) {table}")
                after = conn.execute(_size, dict(table=table)).scalar()
            except DBAPIError as err:
                # A table dropped since it was listed should not end the sweep.
                yield VacuumResult(table, 0, 0, time.time() - t0, str(err.orig))
                continue
            yield VacuumResult(table, before, after, time.time() - t0)


def format_size(n: int) -> str:
    if abs(n) < 1024:
        return f"{n} B"
    value = n / 1024
    for unit in ("kB", "MB", "GB"):
        if abs(value) < 1024:
            return f"{value:,.1f} {unit}"
        value /= 1024
    return f"{value:,.1f} TB"
