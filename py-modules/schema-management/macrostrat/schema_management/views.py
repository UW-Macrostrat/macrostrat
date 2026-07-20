"""Rebuild database views idempotently.

Views are *code*, not stateful structure: they hold no data and are cheap to
recreate. We keep them out of the diff (which would churn/cascade-drop them when
underlying tables change) and instead re-apply them wholesale.

Schema files should contain only ``CREATE VIEW`` (no hand-written ``DROP``s). Each
view is applied with ``CREATE OR REPLACE VIEW`` — which preserves the view's grants
and dependents. When a view's output signature changed incompatibly (SQLSTATE
42P16), ``CREATE OR REPLACE`` can't work, so we recover via the database library's
``on_error`` hook: snapshot the view's grants, ``DROP … CASCADE``, recreate, and
restore the grants. Cascade-dropped dependents are recreated later in the same
dependency-ordered pass.
"""

import re
from dataclasses import dataclass, field
from typing import Iterator

import sqlparse
from sqlalchemy import text

from macrostrat.database import Database
from macrostrat.database.query import StatementContext, StatementDirective
from macrostrat.utils import get_logger

from .rebuild import iter_chunk_statements

log = get_logger(__name__)

# SQLSTATE 42P16 (invalid_table_definition) is what PostgreSQL raises when
# CREATE OR REPLACE VIEW cannot reshape an existing view (dropped/renamed/retyped
# columns). That's our signal to drop and recreate.
_REPLACE_CONFLICT_SQLSTATES = {"42P16"}

_VIEW_STMT_RE = re.compile(r"^\s*create\s+(or\s+replace\s+)?view\b", re.IGNORECASE)
_VIEW_NAME_RE = re.compile(
    r"create\s+(?:or\s+replace\s+)?view\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)",
    re.IGNORECASE,
)


# --- statement collection -------------------------------------------------


def view_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the ``CREATE VIEW`` statements found in a block of SQL."""
    for statement in sqlparse.split(sql_text):
        # Strip comments so a leading comment doesn't hide the verb.
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _VIEW_STMT_RE.match(bare):
            yield bare


def iter_view_statements(chunks) -> Iterator[str]:
    """Yield ``CREATE VIEW`` statements from ``chunks``, in dependency/apply order."""
    yield from iter_chunk_statements(chunks, view_statements_in)


# --- statement helpers ----------------------------------------------------


def _view_name(statement: str) -> str:
    m = _VIEW_NAME_RE.search(statement)
    if m is None:
        raise ValueError(f"Could not parse view name from: {statement[:80]}…")
    return m.group(1)


def _as_create_or_replace(statement: str) -> str:
    """Rewrite ``CREATE VIEW`` → ``CREATE OR REPLACE VIEW`` (leaving the rest)."""
    return _VIEW_STMT_RE.sub(
        lambda m: ("CREATE OR REPLACE VIEW" if not m.group(1) else m.group(0)),
        statement,
        count=1,
    )


def _view_transform(ctx: StatementContext) -> list[StatementDirective] | None:
    """Pre-execution rewrites for view statements.

    Currently just ``CREATE VIEW`` → ``CREATE OR REPLACE VIEW``; this is the place
    to add any further pre-statement modifications. Returning ``None`` runs the
    statement unchanged (already-``OR REPLACE`` views, or non-view statements).
    """
    m = _VIEW_STMT_RE.match(ctx.sql_text)
    if m is not None and not m.group(1):
        return [
            StatementDirective(
                query=_as_create_or_replace(ctx.sql_text), params=ctx.params
            )
        ]
    return None


def _is_replace_conflict(err: Exception) -> bool:
    orig = getattr(err, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return sqlstate in _REPLACE_CONFLICT_SQLSTATES


def _split_qualified(name: str) -> tuple[str | None, str]:
    parts = name.replace('"', "").split(".")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, parts[-1]


def _grant_statements(connectable, schema: str, view: str) -> list[str]:
    """Snapshot the current grants on a view as GRANT statements, so they can be
    restored after a drop-and-recreate."""
    rows = connectable.execute(
        text(
            """
            SELECT grantee, privilege_type
            FROM information_schema.role_table_grants
            WHERE table_schema = :schema AND table_name = :view
            """
        ),
        {"schema": schema, "view": view},
    ).fetchall()
    statements = []
    for grantee, privilege in rows:
        to = "PUBLIC" if grantee.upper() == "PUBLIC" else f'"{grantee}"'
        statements.append(f"GRANT {privilege} ON {schema}.{view} TO {to}")
    return statements


# --- rebuild --------------------------------------------------------------


@dataclass
class ViewRebuildReport:
    total: int = 0
    recreated: list[str] = field(default_factory=list)

    @property
    def replaced(self) -> int:
        """Views updated in place via CREATE OR REPLACE (i.e. not recreated)."""
        return self.total - len(self.recreated)


def _make_recovery(report: ViewRebuildReport):
    """Build an ``on_error`` handler that drops & recreates views whose signature
    changed, restoring their grants."""

    def recover(ctx: StatementContext, err: Exception, connectable):
        if not _is_replace_conflict(err) or not _VIEW_STMT_RE.match(ctx.sql_text):
            return None  # not ours to handle — fall through to normal error handling

        name = _view_name(ctx.sql_text)
        schema, view = _split_qualified(name)

        grants: list[str] = []
        if schema is not None:
            grants = _grant_statements(connectable, schema, view)
        else:
            log.warning("View %s is unqualified; grants will not be restored", name)

        log.info("View %s changed shape; dropping and recreating", name)
        report.recreated.append(name)

        return [
            StatementDirective(query=f"DROP VIEW IF EXISTS {name} CASCADE"),
            StatementDirective(query=ctx.query),  # the original CREATE (OR REPLACE)
            *[StatementDirective(query=g) for g in grants],
        ]

    return recover


def rebuild_views(db: Database, chunks) -> ViewRebuildReport:
    """Re-apply the views in ``chunks``, dropping and recreating only when needed.

    Runs each view through the database library's find-run loop; the drop/recreate
    fallback and grant restoration are handled by an ``on_error`` recovery hook.
    """
    report = ViewRebuildReport()
    recover = _make_recovery(report)

    for statement in iter_view_statements(chunks):
        db.run_sql(
            statement,
            transform_statement=_view_transform,
            on_error=recover,
            raise_errors=False,
        )
        report.total += 1

    return report
