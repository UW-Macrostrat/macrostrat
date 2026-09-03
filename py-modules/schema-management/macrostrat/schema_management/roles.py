"""Re-create the database roles declared in the schema files.

Roles are cluster-level objects, so the schema diff (`plan`/`apply`, backed by
`migra`) cannot see them at all: it compares one database against another and
`CREATE ROLE` is outside that comparison. On a database built by diff rather
than by `provision`, the roles named in ``schema/core/0000-roles.sql`` simply
never exist — and every grant that mentions one then fails.

So roles are swept here and applied *first*, before grants, which is what makes
**`provision` ≡ `diff` + `sync`** true for permissions and not just structure.

The statements are applied as declared: a role that already exists raises
`42710`, which is noted as skipped and stepped over. Nothing here reconciles an
existing role's attributes — that is a change to a live credential, not a
rebuild.
"""

import re
from typing import Iterator

import sqlparse

from macrostrat.database import Database

from .rebuild import RebuildReport, apply_statements, iter_chunk_statements

# `CREATE ROLE`/`CREATE USER` (a documented alias) and `CREATE GROUP`, which the
# schema does not use today but which is the same catalog object.
_ROLE_STMT_RE = re.compile(r"^\s*create\s+(role|user|group)\s+", re.IGNORECASE)

# SQLSTATE 42710 (duplicate_object) — the role is already there, which is the
# expected outcome for most of a sweep and not a failure.
_DUPLICATE_OBJECT = "42710"


def role_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the CREATE ROLE / USER / GROUP statements in a block of SQL."""
    for statement in sqlparse.split(sql_text):
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _ROLE_STMT_RE.match(bare):
            yield bare


def iter_role_statements(chunks) -> Iterator[str]:
    """Yield role-creating statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, role_statements_in)


def role_already_exists(err: Exception) -> bool:
    """Whether ``err`` is the "this role is already there" error."""
    return getattr(getattr(err, "orig", None), "pgcode", None) == _DUPLICATE_OBJECT


def rebuild_roles(db: Database, chunks) -> RebuildReport:
    """Create every role declared in ``chunks``.

    Creating a role needs `CREATEROLE` (or superuser); against a connection with
    neither, the statements are recorded as failed and the rest of the sync
    still runs.
    """
    return apply_statements(
        db, iter_role_statements(chunks), tolerate=role_already_exists
    )
