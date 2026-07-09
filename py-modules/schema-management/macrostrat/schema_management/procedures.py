"""Rebuild database functions and procedures idempotently.

Parallel to the view rebuild: walk the schema chunks in dependency order and
re-apply every ``CREATE FUNCTION`` / ``CREATE PROCEDURE`` as ``CREATE OR REPLACE``.
Functions/procedures are non-data-modifying code that may be interleaved with
other schema; a body change is picked up by ``CREATE OR REPLACE`` without a drop.

Signature changes (SQLSTATE 42P13, "cannot change return type of existing
function") can't be replaced in place — those are handled by the diff
(`plan`/`apply`), so here a failing statement is recorded and skipped.
"""

import re
from typing import Iterator

import sqlparse

from macrostrat.database import Database

from .rebuild import RebuildReport, apply_statements, iter_chunk_statements

_PROC_STMT_RE = re.compile(
    r"^\s*create\s+(or\s+replace\s+)?(function|procedure)\b", re.IGNORECASE
)


def procedure_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the CREATE FUNCTION / PROCEDURE statements in a block of SQL."""
    for statement in sqlparse.split(sql_text):
        # Strip comments so a leading comment doesn't hide the verb.
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _PROC_STMT_RE.match(bare):
            yield bare


def _as_create_or_replace(statement: str) -> str:
    """Rewrite ``CREATE FUNCTION|PROCEDURE`` → ``CREATE OR REPLACE …`` (leaving the rest)."""
    return _PROC_STMT_RE.sub(
        lambda m: (
            m.group(0) if m.group(1) else f"CREATE OR REPLACE {m.group(2).upper()}"
        ),
        statement,
        count=1,
    )


def iter_procedure_statements(chunks) -> Iterator[str]:
    """Yield function/procedure statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, procedure_statements_in)


def rebuild_procedures(db: Database, chunks) -> RebuildReport:
    """Re-apply every function/procedure in ``chunks`` as ``CREATE OR REPLACE``."""
    return apply_statements(
        db, iter_procedure_statements(chunks), transform=_as_create_or_replace
    )
