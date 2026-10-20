"""Ingest the format's example workbooks into one project, as a standing test.

Each workbook becomes its own column group, named after the file, inside the examples
project. Columns are reconciled within a group, so a successful re-run replaces that
example; a workbook with errors is not written at all, so its last good version stays.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .database import ProjectIdentifier
from .ingest import Placement, ingest_columns_from_file
from .notices import IngestValidationError

EXAMPLES_PROJECT = "Ingestion Examples"
#: Examples are published, so they show wherever active columns do.
EXAMPLES_STATUS = "active"

#: The example workbooks, in the column-ingestion format repository (a submodule here).
EXAMPLES_DIR = Path("submodules") / "column-ingestion" / "Examples"


@dataclass
class ExampleResult:
    path: Path
    #: `written`, `checked` (a dry run without errors), or `failed`.
    status: str
    notices: list[dict] = field(default_factory=list)
    summary: dict | None = None
    #: An exception that stopped the ingest, as opposed to errors in the data.
    exception: str | None = None


def examples_dir(srcroot: Path) -> Path:
    return Path(srcroot) / EXAMPLES_DIR


def find_examples(directory: Path) -> list[Path]:
    """The workbooks in `directory`, skipping Excel's `~$` lock files."""
    return sorted(
        p for p in Path(directory).glob("*.xlsx") if not p.name.startswith("~$")
    )


def resolve_example(name: str | Path, directory: Path) -> Path:
    """A path as given, or else a file of that name in the examples folder."""
    path = Path(name)
    if path.exists():
        return path
    candidate = Path(directory) / path
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"No such workbook: {name} (also looked in {directory})")


def ingest_examples(
    db,
    paths: list[Path],
    *,
    project: str = EXAMPLES_PROJECT,
    status_code: str = EXAMPLES_STATUS,
    dry_run: bool = False,
) -> list[ExampleResult]:
    """Ingest each workbook into `project`, one column group per file."""
    results = []
    for path in paths:
        placement = Placement(
            project=ProjectIdentifier(name=project),
            col_group=Path(path).stem,
            status_code=status_code,
        )
        try:
            result = ingest_columns_from_file(
                db, path, dry_run=dry_run, placement=placement
            )
        except IngestValidationError as err:
            results.append(ExampleResult(path, "failed", err.notices.to_list()))
            continue
        except Exception as err:
            # One broken workbook should not stop the rest from being tried
            db.session.rollback()
            results.append(ExampleResult(path, "failed", exception=repr(err)))
            continue
        status = "checked" if dry_run else "written"
        if not result["ok"]:
            status = "failed"
        results.append(
            ExampleResult(path, status, result["notices"], result["summary"])
        )
    return results
