"""Rebuild database grants idempotently.

Walks a set of schema chunks in dependency order and re-applies every ``GRANT`` /
``REVOKE`` / ``ALTER DEFAULT PRIVILEGES`` statement. These are idempotent, so this
restores the *declared* permission state — useful after a view drop/recreate that
lost a dependent's grants, or any time permissions have drifted from the source.
"""

import re
from typing import Iterator

import sqlparse

from macrostrat.database import Database

from .rebuild import RebuildReport, apply_statements, iter_chunk_statements

# Statements that (re)assign permissions.
_GRANT_STMT_RE = re.compile(
    r"^\s*(grant|revoke|alter\s+default\s+privileges)\b", re.IGNORECASE
)


def grant_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the GRANT / REVOKE / ALTER DEFAULT PRIVILEGES statements in a block of SQL."""
    for statement in sqlparse.split(sql_text):
        # Strip comments so a leading comment doesn't hide the verb.
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _GRANT_STMT_RE.match(bare):
            yield bare


def iter_grant_statements(chunks) -> Iterator[str]:
    """Yield permission statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, grant_statements_in)


def rebuild_grants(db: Database, chunks) -> RebuildReport:
    """Re-apply every declared grant in ``chunks``, in dependency order.

    ``GRANT``/``REVOKE`` are idempotent, so this restores the intended permission
    state; failing statements (e.g. a grant on an object absent here) are recorded
    and skipped.
    """
    return apply_statements(db, iter_grant_statements(chunks))
