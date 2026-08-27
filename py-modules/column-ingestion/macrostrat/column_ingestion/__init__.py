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
def ingest_columns(
    data_file: Path = Argument(..., help="Path to the data file to ingest"),
):
    """Ingest columns from tabular data."""
    from .ingest import ingest_columns_from_file

    db = get_database()
    ingest_columns_from_file(db, data_file)


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
