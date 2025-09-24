from typer import Argument, Typer

from macrostrat.core.migrations import run_migrations
from .gbdb import update_age_model
from .schema import IntegrationsBaseSchema
from .strabospot import populate_strabospot

pipelines = {
    "strabospot": populate_strabospot,
    "update-gbdb-age-model": update_age_model,
}


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
    """Run migrations for the integrations subsystem"""
    run_migrations(
        subsystem="integrations",
        apply=apply,
        force=force,
        data_changes=data_changes,
    )


@app.command()
def run(pipeline: str = Argument(None)):
    """Run a pipeline"""
    if pipeline is None:
        print("Please specify a pipeline")
        print("Available pipelines:")
        for key in pipelines.keys():
            print(f"  {key}")
        return

    pipelines[pipeline]()
