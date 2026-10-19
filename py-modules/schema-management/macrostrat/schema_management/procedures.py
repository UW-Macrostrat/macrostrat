"""Rebuild database functions and procedures idempotently.

Parallel to the view rebuild: walk the schema chunks in dependency order and
re-apply every ``CREATE FUNCTION`` / ``CREATE PROCEDURE`` as ``CREATE OR REPLACE``.
Functions/procedures are non-data-modifying code that may be interleaved with
other schema; a body change is picked up by ``CREATE OR REPLACE`` without a drop.

A change ``CREATE OR REPLACE`` refuses (SQLSTATE 42P13: a renamed parameter, a
new return type, a removed default) is applied by dropping the function and
recreating it in one transaction, with its ``EXECUTE`` grants restored. The
input types are unchanged in such a conflict, or the statement would have made
a new overload, so the old signature is the new one. Dependents are not
cascaded: a function a view or trigger depends on fails the drop, and the
transaction leaves the old definition in place. So does an overloaded name,
whose conflicting signature cannot be told apart here.
"""

import re
from typing import Iterator

import sqlparse
from sqlalchemy import text

from macrostrat.database import Database
from macrostrat.utils import get_logger

from .rebuild import (
    ChunkStatement,
    RebuildReport,
    apply_statements,
    iter_chunk_statements,
)
from .views import _is_conflict, _split_qualified

log = get_logger(__name__)

_PROC_STMT_RE = re.compile(
    r"^\s*create\s+(or\s+replace\s+)?(function|procedure)\b", re.IGNORECASE
)
_PROC_NAME_RE = re.compile(
    r"^\s*create\s+(?:or\s+replace\s+)?(function|procedure)\s+([\w.\"]+)\s*\(",
    re.IGNORECASE,
)

# SQLSTATE 42P13 (invalid_function_definition). Also raised for a body that does
# not match its declared result, which the recreate then fails on and rolls back.
_REPLACE_CONFLICT_SQLSTATES = {"42P13"}

# The existing definitions of a name: signature, and who may execute it when its
# privileges differ from the default (a NULL `proacl`).
_EXISTING = """
SELECT
  p.oid::regprocedure::text AS identity,
  p.proacl IS NOT NULL AS has_acl,
  coalesce(
    array_agg(
      CASE WHEN a.grantee = 0 THEN 'PUBLIC' ELSE a.grantee::regrole::text END
    ) FILTER (WHERE a.privilege_type = 'EXECUTE'),
    '{}'
  ) AS grantees
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
LEFT JOIN LATERAL aclexplode(p.proacl) a ON true
WHERE n.nspname = :schema AND p.proname = :name
GROUP BY p.oid
"""


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


def iter_procedure_statements(chunks) -> Iterator[ChunkStatement]:
    """Yield function/procedure statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, procedure_statements_in)


def _recreate(db: Database, statement: str, err: Exception) -> bool:
    """Drop and recreate a function ``CREATE OR REPLACE`` could not change."""
    m = _PROC_NAME_RE.match(statement)
    if not _is_conflict(err, _REPLACE_CONFLICT_SQLSTATES) or m is None:
        return False
    kind, name = m.group(1).upper(), m.group(2)
    schema, proname = _split_qualified(name)
    if schema is None:
        return False

    with db.engine.begin() as conn:
        existing = conn.execute(
            text(_EXISTING), {"schema": schema, "name": proname}
        ).fetchall()
        if len(existing) != 1:
            raise RuntimeError(
                f"{name} has {len(existing)} signatures; drop the old one explicitly"
            )
        identity, has_acl, grantees = existing[0]
        conn.exec_driver_sql(f"DROP {kind} {identity}")
        conn.exec_driver_sql(statement)
        if has_acl:
            conn.exec_driver_sql(f"REVOKE ALL ON {kind} {identity} FROM PUBLIC")
            for grantee in grantees:
                conn.exec_driver_sql(f"GRANT EXECUTE ON {kind} {identity} TO {grantee}")
    log.info("%s changed signature; dropped and recreated", identity)
    return True


def rebuild_procedures(db: Database, chunks) -> RebuildReport:
    """Re-apply every function/procedure in ``chunks`` as ``CREATE OR REPLACE``."""
    return apply_statements(
        db,
        iter_procedure_statements(chunks),
        transform=_as_create_or_replace,
        recover=_recreate,
    )
