from typer import Typer

from macrostrat.core.migrations import run_migrations
from .schema import StrabospotBaseSchema

app = Typer(
    no_args_is_help=True,
    help="StraboSpot structural geology data system",
)


@app.command()
def migrate(
    apply: bool = False,
    force: bool = False,
    data_changes: bool = False,
):
    """Run migrations for the StraboSpot integration"""
    run_migrations(
        subsystem="strabospot-integration",
        apply=apply,
        force=force,
        data_changes=data_changes,
    )
