"""Re-apply idempotent seed data from the schema chunks.

Alongside DDL, the schema files carry a few data-creating statements — ``INSERT``
/ ``UPDATE`` (sometimes as ``WITH … INSERT``) that populate reference / seed rows.
The diff (`plan`/`apply`) is blind to data, so these would be missing after a
diff-based deploy. Re-applying them here means **`provision` ≡ `diff` + `sync`**:
the same schema *and* seed data either way.

These statements are expected to be idempotent (e.g. ``INSERT … ON CONFLICT``);
``rebuild_seed`` warns about an ``INSERT`` that lacks an ``ON CONFLICT`` clause,
since re-applying it may duplicate rows or fail.
"""

import re
from typing import Iterator, Optional

import sqlparse

from macrostrat.database import Database
from macrostrat.utils import get_logger

from .rebuild import (
    ChunkStatement,
    RebuildReport,
    apply_statements,
    iter_chunk_statements,
)
from .selection import ObjectName, ObjectSelector, parse_object_name

log = get_logger(__name__)

# Data-writing DML we sweep in. `sqlparse` classifies these by terminal verb,
# so `WITH … INSERT`/`WITH … UPDATE` are caught while `WITH … SELECT` is not.
_SEED_TYPES = {"INSERT", "UPDATE", "DELETE", "MERGE"}

# `SELECT setval(…)` writes — it realigns a sequence with the rows a seed INSERT
# just wrote — but `sqlparse` types it as a SELECT, so it slips past `_SEED_TYPES`
# and a re-seeded table is left handing out keys that already exist. Matched on
# the call rather than the statement type; `setval` has no read-only reading.
_SETVAL_RE = re.compile(r"\bsetval\s*\(", re.IGNORECASE)

# The table a data statement writes. `DO UPDATE` (an upsert) and `FOR UPDATE`
# (a lock) name no target.
_TARGET_RE = re.compile(
    r"(?<!\bdo )(?<!\bfor )\b(?:insert into|update|delete from|merge into)"
    r"\s+(?:only\s+)?([\w.\"]+)",
    re.IGNORECASE,
)
_SETVAL_SEQUENCE_RE = re.compile(
    r"\bsetval\s*\(\s*(?:pg_get_serial_sequence\s*\(\s*)?'([^']+)'", re.IGNORECASE
)
_FROM_RE = re.compile(r"\bfrom\s+([\w.\"]+)", re.IGNORECASE)


def data_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the data-writing statements in a block of SQL.

    That is INSERT/UPDATE/DELETE/MERGE (including their `WITH …` forms), plus
    the `SELECT setval(…)` calls that go with a seed insert.
    """
    for statement in sqlparse.parse(sql_text):
        kind = statement.get_type()
        bare = sqlparse.format(str(statement), strip_comments=True).strip()
        if not bare:
            continue
        if kind in _SEED_TYPES:
            yield bare
        elif kind == "SELECT" and _SETVAL_RE.search(bare):
            yield bare


def data_objects(statement: str) -> list[ObjectName]:
    """The tables a statement writes; for ``setval``, its sequence and source table."""
    flat = " ".join(statement.split())
    names = _TARGET_RE.findall(flat)
    if _SETVAL_RE.search(flat):
        names += _SETVAL_SEQUENCE_RE.findall(flat) + _FROM_RE.findall(flat)
    return [parse_object_name(n) for n in names]


def iter_seed_statements(
    chunks, only: Optional[ObjectSelector] = None
) -> Iterator[ChunkStatement]:
    """Yield seed-data statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, data_statements_in, only, data_objects)


def _is_non_idempotent_insert(statement: str) -> bool:
    """An INSERT (possibly ``WITH … INSERT``) with no ON CONFLICT clause."""
    parsed = sqlparse.parse(statement)
    if not parsed or parsed[0].get_type() != "INSERT":
        return False
    return "on conflict" not in statement.lower()


def rebuild_seed_data(
    db: Database, chunks, only: Optional[ObjectSelector] = None
) -> RebuildReport:
    """Re-apply every seed-data statement in ``chunks``, in dependency order.

    Statements are expected to be idempotent; a non-idempotent INSERT is warned
    about (and, if it then conflicts on re-apply, recorded as failed rather than
    aborting the run).
    """
    statements = list(iter_seed_statements(chunks, only))
    for statement in statements:
        if _is_non_idempotent_insert(statement.sql):
            log.warning(
                "Seed INSERT lacks ON CONFLICT (may not be idempotent): %s",
                statement.sql[:120],
            )
    return apply_statements(db, statements)
