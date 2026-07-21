from typer import Argument, Typer

from macrostrat.schema_management.migrations import run_migrations

from .gbdb import app as gbdb_app
from .gbdb import update_age_model
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
def run(pipeline: str = Argument(None)):
    """Run a pipeline"""
    if pipeline is None:
        print("Please specify a pipeline")
        print("Available pipelines:")
        for key in pipelines.keys():
            print(f"  {key}")
        return

    pipelines[pipeline]()


app.add_typer(gbdb_app, name="gbdb")
