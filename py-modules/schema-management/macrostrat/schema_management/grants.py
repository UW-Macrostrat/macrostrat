"""Rebuild database grants idempotently.

Parallel to the view rebuild (``views.py``): walk the schema chunks in dependency
order and re-apply every ``GRANT`` / ``REVOKE`` / ``ALTER DEFAULT PRIVILEGES``
statement. These are idempotent, so this simply restores the *declared* permission
state — useful after a view drop/recreate that lost a dependent's grants, or any
time permissions have drifted from the schema source.

Grants stay diff-managed like other structure; this is a convenience for
re-asserting them without a full ``plan``/``apply`` cycle.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import sqlparse

from macrostrat.core.schema_definition import sql_files
from macrostrat.database import Database
from macrostrat.utils import get_logger

from .chunks import chunks_for_environment
from .composer import order_chunks

log = get_logger(__name__)

# Statements that (re)assign permissions.
_GRANT_STMT_RE = re.compile(
    r"^\s*(grant|revoke|alter\s+default\s+privileges)\b", re.IGNORECASE
)


# --- statement collection -------------------------------------------------


def grant_statements_in(sql_text: str) -> Iterator[str]:
    """Yield the GRANT / REVOKE / ALTER DEFAULT PRIVILEGES statements in a block of SQL."""
    for statement in sqlparse.split(sql_text):
        # Strip comments so a leading comment doesn't hide the verb.
        bare = sqlparse.format(statement, strip_comments=True).strip()
        if _GRANT_STMT_RE.match(bare):
            yield bare


def iter_grant_statements(env: str) -> Iterator[str]:
    """Yield permission statements for ``env`` in dependency/apply order.

    Only file-backed providers are scanned; function-backed providers manage
    their own objects (and grants) themselves.
    """
    for chunk in order_chunks(chunks_for_environment(env)):
        for provider in chunk.provides:
            if not isinstance(provider, Path):
                continue
            for f in sql_files(provider):
                yield from grant_statements_in(f.read_text())


# --- rebuild --------------------------------------------------------------


@dataclass
class GrantRebuildReport:
    total: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def applied(self) -> int:
        return self.total - len(self.failed)


def rebuild_grants(db: Database, env: str) -> GrantRebuildReport:
    """Re-apply every declared grant for ``env``, in dependency order.

    ``GRANT``/``REVOKE`` are idempotent, so this restores the intended permission
    state. A statement that fails (e.g. a grant on an object not present in this
    environment) is recorded and skipped rather than aborting the rebuild.
    """
    report = GrantRebuildReport()
    for statement in iter_grant_statements(env):
        report.total += 1
        try:
            db.run_sql(statement, raise_errors=True)
        except Exception as err:  # noqa: BLE001 — best-effort; record and continue
            log.warning("Grant statement failed (%s): %s", err, statement[:100])
            report.failed.append(statement)
    return report
