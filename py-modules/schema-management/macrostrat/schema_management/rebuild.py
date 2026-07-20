"""Shared infrastructure for rebuilding non-data-modifying schema objects.

Views, procedures/functions, and grants are all cheap, idempotent schema
elements that may be interleaved with other DDL in the schema files. Each has its
own module (`views`, `procedures`, `grants`); this module holds what they share:
walking a set of chunks for matching statements, a best-effort apply driver with
a report, and the reusable ``--target`` / ``--no-dependents`` CLI option block.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional

from typer import Option

from macrostrat.core.schema_definition import sql_files
from macrostrat.database import Database
from macrostrat.utils import get_logger

log = get_logger(__name__)


def iter_chunk_statements(
    chunks, extract: Callable[[str], Iterator[str]]
) -> Iterator[str]:
    """Yield statements from the file-backed providers of ``chunks`` (in order).

    ``extract`` pulls the statements of interest out of one SQL file's text.
    Function-backed providers manage their own objects and are skipped.
    """
    for chunk in chunks:
        for provider in chunk.provides:
            if not isinstance(provider, Path):
                continue
            for f in sql_files(provider):
                yield from extract(f.read_text())


@dataclass
class RebuildReport:
    total: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def applied(self) -> int:
        return self.total - len(self.failed)


def apply_statements(
    db: Database,
    statements: Iterator[str],
    *,
    transform: Optional[Callable[[str], str]] = None,
) -> RebuildReport:
    """Best-effort: run each statement, recording (not raising on) failures.

    ``transform`` optionally rewrites a statement before it runs (e.g. ``CREATE`` →
    ``CREATE OR REPLACE``). A statement that fails — e.g. a grant on an object
    absent in this environment — is logged and skipped so the rebuild completes.
    """
    report = RebuildReport()
    for statement in statements:
        report.total += 1
        sql = transform(statement) if transform is not None else statement
        try:
            db.run_sql(sql, raise_errors=True)
        except Exception as err:  # noqa: BLE001 — best-effort; record and continue
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
