"""Re-create the database roles declared in the schema files.

Roles are cluster-level objects, so the schema diff (`plan`/`apply`, backed by
`migra`) cannot see them at all: it compares one database against another and
`CREATE ROLE` is outside that comparison. On a database built by diff rather
than by `provision`, the roles named in ``schema/core/0000-roles.sql`` simply
never exist — and every grant that mentions one then fails, silently, because
`sync`'s grant pass is best-effort.

So roles are swept here and applied *first*, before grants, which is what makes
**`provision` ≡ `diff` + `sync`** true for permissions and not just for
structure.

`CREATE ROLE` has no `IF NOT EXISTS`, so each statement is wrapped in a `DO`
block guarded on `pg_roles`; re-applying a role that already exists is a no-op
rather than a `42710`. Attribute drift on an existing role (say, a role that
gained `LOGIN` by hand) is deliberately *not* reconciled — that is a change to
a live credential, not a rebuild.
"""

import re
from typing import Iterator

import sqlparse

from macrostrat.database import Database
from macrostrat.utils import get_logger

from .rebuild import RebuildReport, apply_statements, iter_chunk_statements

log = get_logger(__name__)

# `CREATE ROLE`/`CREATE USER` (`USER` is a documented alias) — and `CREATE GROUP`,
# which the schema does not use today but which is the same catalog object.
_ROLE_STMT_RE = re.compile(r"^\s*create\s+(role|user|group)\s+", re.IGNORECASE)

# The role name that follows the verb: a bare identifier or a quoted one
# (Macrostrat has both — `macrostrat_admin` and `"macrostrat-admin"`).
_ROLE_NAME_RE = re.compile(
    r"^\s*create\s+(?:role|user|group)\s+(\"[^\"]+\"|[A-Za-z_][A-Za-z0-9_$]*)",
    re.IGNORECASE,
)


def role_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the CREATE ROLE / USER / GROUP statements in a block of SQL."""
    for statement in sqlparse.split(sql_text):
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _ROLE_STMT_RE.match(bare):
            yield bare


def iter_role_statements(chunks) -> Iterator[str]:
    """Yield role-creating statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, role_statements_in)


def role_name_in(statement: str) -> str | None:
    """The role name a ``CREATE ROLE`` statement declares, unquoted."""
    match = _ROLE_NAME_RE.match(statement)
    if match is None:
        return None
    name = match.group(1)
    return name[1:-1] if name.startswith('"') else name


def guard_existing(statement: str) -> str:
    """Wrap a ``CREATE ROLE`` so an already-present role is a no-op.

    The role name is passed as a quoted *literal* into the `pg_roles` lookup and
    the statement itself is inlined verbatim, so nothing is reconstructed by
    string formatting (which is also why there is no `%`-style `format()` here —
    a bare `%` in SQL run through SQLAlchemy is read as a bind parameter).
    """
    name = role_name_in(statement)
    if name is None:
        return statement
    body = statement.rstrip().rstrip(";")
    literal = name.replace("'", "''")
    return (
        "DO $sync_role$ BEGIN\n"
        f"  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{literal}') THEN\n"
        f"    {body};\n"
        "  END IF;\n"
        "END $sync_role$;"
    )


def rebuild_roles(db: Database, chunks) -> RebuildReport:
    """Create every role declared in ``chunks`` that does not already exist.

    Creating a role needs `CREATEROLE` (or superuser); against a connection that
    has neither, the statements are recorded as failed and the rest of the sync
    still runs.
    """
    return apply_statements(db, iter_role_statements(chunks), transform=guard_existing)
