"""Rebuild database roles and grants idempotently.

Walks a set of schema chunks in dependency order and re-applies every
``CREATE ROLE`` / ``GRANT`` / ``REVOKE`` / ``ALTER DEFAULT PRIVILEGES`` statement:
the permission state the schema declares, restored — useful after a view
drop/recreate that lost a dependent's grants, or any time permissions have
drifted from the source.

Roles belong here rather than in a pass of their own. They are cluster-level
objects, so the schema diff (`plan`/`apply`, backed by `migra`) cannot see them
at all — on a database built by diff rather than `provision`, the roles named in
``schema/core/0000-roles.sql`` never exist and every grant mentioning one fails.
Sweeping them alongside grants keeps them in **declared order**, which is what
matters: that file interleaves the two, each ``GRANT`` following the role it
needs. A separate roles-first pass would reorder them for no benefit.

Statements are applied as declared. A role that already exists raises `42710`,
which is noted as skipped and stepped over; nothing here reconciles an existing
role's attributes, which is a change to a live credential rather than a rebuild.
"""

import re
from typing import Iterator

import sqlparse

from macrostrat.database import Database

from .rebuild import RebuildReport, apply_statements, iter_chunk_statements

# Statements that create a principal or (re)assign permissions. `CREATE USER` and
# `CREATE GROUP` are documented aliases for `CREATE ROLE` — the same catalog object.
_PERMISSION_STMT_RE = re.compile(
    r"^\s*(create\s+(role|user|group)|grant|revoke|alter\s+default\s+privileges)\b",
    re.IGNORECASE,
)

# SQLSTATE 42710 (duplicate_object) — the role is already there, which is the
# expected outcome for most of a sweep and not a failure.
_DUPLICATE_OBJECT = "42710"


def grant_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the role/permission statements in a block of SQL, in declared order."""
    for statement in sqlparse.split(sql_text):
        # Strip comments so a leading comment doesn't hide the verb.
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _PERMISSION_STMT_RE.match(bare):
            yield bare


def iter_grant_statements(chunks) -> Iterator[str]:
    """Yield permission statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, grant_statements_in)


def object_already_exists(err: Exception) -> bool:
    """Whether ``err`` is the "this object is already there" error.

    Read from the driver exception SQLAlchemy wraps (``.orig``). psycopg 3 spells
    the code ``sqlstate`` and psycopg 2 ``pgcode``; both drivers are installed
    here, so check for either rather than matching on the message text.
    """
    orig = getattr(err, "orig", err)
    code = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return code == _DUPLICATE_OBJECT


def rebuild_grants(db: Database, chunks) -> RebuildReport:
    """Re-apply every declared role and grant in ``chunks``, in dependency order.

    Creating a role needs `CREATEROLE` (or superuser); against a connection with
    neither, those statements are recorded as failed and the rest still runs — as
    does a grant on an object absent in this environment.
    """
    return apply_statements(
        db, iter_grant_statements(chunks), tolerate=object_already_exists
    )
