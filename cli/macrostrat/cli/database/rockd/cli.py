import typer, importlib
from .database import get_rockd_db
from typer import Option
from macrostrat.core.migrations import run_migrations



cli = typer.Typer(help="Rockd database tools")

@cli.command()
def migrations(
    apply: bool = typer.Option(False, "--apply", help="Actually run them"),
    name: str | None = None,
    force: bool = False,
    data_changes: bool = False,
):
    """
    List or apply Rockd migrations.
    """
    # Ensure the package (and its Migration subclasses) are imported
    importlib.import_module("macrostrat.cli.database.rockd.migrations")

    db = get_rockd_db()
    run_migrations(
        apply=apply,
        name=name,
        force=force,
        data_changes=data_changes,
        subsystem="rockd",
    )
