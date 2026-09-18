"""Shared infrastructure for rebuilding non-data-modifying schema objects.

Views, procedures/functions, and grants are all cheap, idempotent schema
elements that may be interleaved with other DDL in the schema files. Each has its
own module (`views`, `procedures`, `grants`); this module holds what they share:
walking a set of chunks for matching statements, a best-effort apply driver with
a report, and the reusable ``--target`` / ``--no-dependents`` CLI option block.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, NamedTuple, Optional

from typer import Option

from macrostrat.core.schema_definition import sql_files
from macrostrat.database import Database
from macrostrat.utils import get_logger

from .composer import set_applying_role

log = get_logger(__name__)


class ChunkStatement(NamedTuple):
    """A statement together with the role its chunk is applied as.

    A rebuild re-applies the same SQL the declarative build does, so it must run
    it as the same role: an object it recreates is then born with the owner
    ``build_schema`` would have given it, rather than the connector's.
    """

    owner: Optional[str]
    sql: str


def iter_chunk_statements(
    chunks, extract: Callable[[str], Iterator[str]]
) -> Iterator[ChunkStatement]:
    """Yield statements from the file-backed providers of ``chunks`` (in order).

    ``extract`` pulls the statements of interest out of one SQL file's text.
    Function-backed providers manage their own objects and are skipped.
    """
    for chunk in chunks:
        for provider in chunk.provides:
            if not isinstance(provider, Path):
                continue
            for f in sql_files(provider):
                for statement in extract(f.read_text()):
                    yield ChunkStatement(chunk.owner, statement)


# Distinct from ``None``, which is a real owner (the connector), so the first
# statement of a sweep always establishes a role rather than inheriting one.
_UNSET = object()


@contextmanager
def role_switcher(db: Database):
    """Yield ``use(owner)``, which applies subsequent statements as ``owner``.

    The role is re-established only when it changes, and always reset on exit —
    ``SET ROLE`` is session-level, so a sweep must not leave the session
    masquerading as an application role (the same contract as ``build_schema``).
    """
    current = _UNSET

    def use(owner: Optional[str]) -> None:
        nonlocal current
        if owner != current:
            set_applying_role(db, owner)
            current = owner

    try:
        yield use
    finally:
        # These sweeps are best-effort, so the reset must not turn a recorded
        # failure into a raise. A `SET ROLE` is itself rolled back with the
        # transaction, so the one case this swallows — an aborted transaction —
        # is also the one where the role is already gone.
        db.run_sql("RESET ROLE", raise_errors=False)


@dataclass
class RebuildReport:
    total: int = 0
    failed: list[str] = field(default_factory=list)
    # Statements whose failure was expected and is not worth reporting as one —
    # e.g. creating a role that is already there.
    skipped: list[str] = field(default_factory=list)

    @property
    def applied(self) -> int:
        return self.total - len(self.failed) - len(self.skipped)


def apply_statements(
    db: Database,
    statements: Iterator[ChunkStatement],
    *,
    transform: Optional[Callable[[str], str]] = None,
    tolerate: Optional[Callable[[Exception], bool]] = None,
) -> RebuildReport:
    """Best-effort: run each statement, recording (not raising on) failures.

    Each statement runs as its chunk's owner, so the sweep reproduces the
    declarative build's ownership rather than the connector's.

    ``transform`` optionally rewrites a statement before it runs (e.g. ``CREATE`` →
    ``CREATE OR REPLACE``). A statement that fails — e.g. a grant on an object
    absent in this environment — is logged and skipped so the rebuild completes.

    ``tolerate`` recognizes an error that is an expected outcome rather than a
    problem (an object that already exists, say); those are counted as skipped
    and left out of the failure report.
    """
    report = RebuildReport()
    with role_switcher(db) as use_role:
        for owner, statement in statements:
            use_role(owner)
            report.total += 1
            sql = transform(statement) if transform is not None else statement
            try:
                db.run_sql(sql, raise_errors=True)
            except Exception as err:  # noqa: BLE001 — best-effort, so record
                if tolerate is not None and tolerate(err):
                    report.skipped.append(statement)
                    continue
                log.warning("statement failed (%s): %s", err, str(sql)[:100])
                report.failed.append(statement)
    return report


# --- reusable CLI option block --------------------------------------------
#
# Shared across commands (e.g. `sync`, `provision`) so target selection is
# consistent. Resolve the values with ``composer.selected_chunks``.

TARGET_OPTION = Option(
    None,
    "--target",
    help="Restrict to a subsystem (chunk); its dependencies are included "
    "unless --no-dependents.",
)

NO_DEPENDENTS_OPTION = Option(
    False,
    "--no-dependents",
    help="With --target, act on only that chunk, not the chunks it depends on.",
)
