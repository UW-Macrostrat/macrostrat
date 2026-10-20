from pathlib import Path
from typing import Optional

from rich.console import Console
from typer import Argument, Option, Typer

from macrostrat.core.database import get_database

from .age_model import AgeModelApproach

console = Console()

app = Typer(
    no_args_is_help=True,
    help="Column ingestion subsystem for Macrostrat",
)


@app.command(name="ingest")
def ingest_command(
    data_file: Path = Argument(..., help="Path to the data file to ingest"),
    dry_run: bool = Option(
        False, "--dry-run", help="Validate the file and roll back without persisting."
    ),
):
    """Ingest columns from tabular data."""
    from .ingest import ingest_columns_from_file
    from .notices import IngestValidationError

    db = get_database()
    try:
        result = ingest_columns_from_file(db, data_file, dry_run=dry_run)
    except IngestValidationError as err:
        print_notices(err.notices.to_list())
        console.print("[red bold]Not written:[/] the data has errors (see above).")
        raise SystemExit(1)
    print_notices(result["notices"])
    summary = result["summary"]
    if summary is not None:
        verb = "Would write" if dry_run else "Wrote"
        console.print(
            f"{verb} {summary['n_columns']} column(s), {summary['n_units']} unit(s) "
            f"into project [bold]{summary['project']['name']}[/]"
        )
    if dry_run:
        console.print("[dim]Dry run — nothing was persisted.[/]")


@app.command(name="create-examples")
def create_examples_command(
    files: Optional[list[Path]] = Argument(
        None,
        help="Workbooks to ingest: paths, or names in the examples folder. "
        "Default: every workbook in the examples folder.",
    ),
    project: str = Option(
        "Ingestion Examples", "--project", help="Project to ingest the examples into."
    ),
    status: str = Option(
        "active", "--status", help="Status for every column (`status_code`)."
    ),
    dry_run: bool = Option(
        False, "--dry-run", help="Validate each workbook and roll back."
    ),
    verbose: bool = Option(False, "--verbose", "-v", help="Show every notice."),
):
    """Ingest the format's example workbooks into one project, one group per file.

    A workbook that ingests replaces its previous version; one with errors is left
    as it was.
    """
    from macrostrat.core.config import settings

    from .examples import examples_dir, find_examples, ingest_examples, resolve_example

    directory = examples_dir(settings.srcroot)
    if files:
        paths = [resolve_example(f, directory) for f in files]
    else:
        paths = find_examples(directory)
    if not paths:
        console.print(f"[red]No workbooks found in {directory}[/]")
        raise SystemExit(1)

    db = get_database()
    results = ingest_examples(
        db, paths, project=project, status_code=status, dry_run=dry_run
    )

    styles = {"written": "green", "checked": "green", "failed": "red bold"}
    for result in results:
        counts = {"error": 0, "warning": 0}
        for notice in result.notices:
            counts[notice["level"]] = counts.get(notice["level"], 0) + 1
        detail = f"{counts['error']} error(s), {counts['warning']} warning(s)"
        if result.summary is not None:
            detail = (
                f"{result.summary['n_columns']} column(s), "
                f"{result.summary['n_units']} unit(s); {detail}"
            )
        console.print(
            f"[{styles[result.status]}]{result.status:8}[/] {result.path.name}: {detail}"
        )
        if result.exception is not None:
            console.print(f"         [red]{result.exception}[/]")
        if verbose or result.status == "failed":
            print_notices(
                [n for n in result.notices if verbose or n["level"] == "error"]
            )

    failed = [r for r in results if r.status == "failed"]
    if dry_run:
        console.print("[dim]Dry run — nothing was persisted.[/]")
    if failed:
        console.print(
            f"[red bold]{len(failed)} of {len(results)} example(s) failed;[/] "
            "their previous versions were kept."
        )
        raise SystemExit(1)


NOTICE_STYLES = {"error": "red bold", "warning": "yellow", "info": "dim"}


def print_notices(items: list[dict]):
    """One line per notice: level, code, where, message."""
    for notice in items:
        level = notice["level"]
        where = [
            f"{key} {notice[key]}"
            for key in ("sheet", "row", "col_id", "unit", "column")
            if notice.get(key) is not None
        ]
        location = f" [dim]({', '.join(where)})[/]" if where else ""
        console.print(
            f"[{NOTICE_STYLES.get(level, '')}]{level:7}[/] {notice['code']}: "
            f"{notice['message']}{location}"
        )


age_model_app = Typer(
    no_args_is_help=True,
    help="Build and inspect column age models",
)
app.add_typer(age_model_app, name="age-model")


@age_model_app.command(name="recalculate")
def recalculate_age_model(
    col_id: int = Argument(..., help="Column ID to rebuild the age model for"),
    approach: Optional[AgeModelApproach] = Option(
        None,
        "--approach",
        help=(
            "How to derive age constraints. Defaults to the approach registered for "
            "the column's project (e.g. 'eodp' for ocean-drilling columns)."
        ),
    ),
    dry_run: bool = Option(
        False, "--dry-run", help="Report what would change without writing."
    ),
):
    """Recalculate a column's age model.

    Existing boundaries are reconciled rather than recreated, so surfaces that have
    not moved keep their identity. Re-running an unchanged column is a no-op.
    """
    from .age_model import recalculate_column_age_model

    db = get_database()
    used, plans = recalculate_column_age_model(
        db, col_id, approach=approach, dry_run=dry_run
    )

    verb = "Would rebuild" if dry_run else "Rebuilt"
    console.print(
        f"{verb} column [bold cyan]{col_id}[/] using the [bold]{used.value}[/] approach"
    )
    if not plans:
        console.print("  [yellow]no sections were modeled[/]")
        return

    for section_id, plan in sorted(plans.items()):
        marker = "[dim]" if plan.is_noop else ""
        console.print(f"  {marker}section {section_id}: {plan}")
