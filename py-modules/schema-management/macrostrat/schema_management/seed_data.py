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

from typing import Iterator

import sqlparse

from macrostrat.database import Database
from macrostrat.utils import get_logger

from .rebuild import RebuildReport, apply_statements, iter_chunk_statements

log = get_logger(__name__)

# Data-writing DML we sweep in. `sqlparse` classifies these by terminal verb,
# so `WITH … INSERT`/`WITH … UPDATE` are caught while `WITH … SELECT` is not.
_SEED_TYPES = {"INSERT", "UPDATE", "DELETE", "MERGE"}


def data_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the data-writing (INSERT/UPDATE/DELETE/MERGE) statements in a block of SQL."""
    for statement in sqlparse.parse(sql_text):
        if statement.get_type() in _SEED_TYPES:
            bare = sqlparse.format(str(statement), strip_comments=True).strip()
            if bare:
                yield bare


def iter_seed_statements(chunks) -> Iterator[str]:
    """Yield seed-data statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, data_statements_in)


def _is_non_idempotent_insert(statement: str) -> bool:
    """An INSERT (possibly ``WITH … INSERT``) with no ON CONFLICT clause."""
    parsed = sqlparse.parse(statement)
    if not parsed or parsed[0].get_type() != "INSERT":
        return False
    return "on conflict" not in statement.lower()


def rebuild_seed_data(db: Database, chunks) -> RebuildReport:
    """Re-apply every seed-data statement in ``chunks``, in dependency order.

    Statements are expected to be idempotent; a non-idempotent INSERT is warned
    about (and, if it then conflicts on re-apply, recorded as failed rather than
    aborting the run).
    """
    statements = list(iter_seed_statements(chunks))
    for statement in statements:
        if _is_non_idempotent_insert(statement):
            log.warning(
                "Seed INSERT lacks ON CONFLICT (may not be idempotent): %s",
                statement[:120],
            )
    return apply_statements(db, statements)
