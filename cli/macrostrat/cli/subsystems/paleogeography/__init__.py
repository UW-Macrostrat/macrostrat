from os import environ
from sys import stderr

from typer import Context, Typer

from ...database import get_db
from .corelle import build_carto_plate_index, create_corelle_fixtures


def load_paleogeography_subsystem(app, main, db_subsystem):
    if app.settings.pg_database is None:
        print("No database configured, skipping corelle subsystem", file=stderr)
        return app

    try:
        environ["CORELLE_DB"] = app.settings.pg_database
        from corelle.engine import cli as corelle_cli
        from corelle.engine.database import initialize
    except ImportError as err:
        print("Corelle subsystem not available", err, file=stderr)
        return app

    paleo_app = Typer(name="paleogeography", no_args_is_help=True)

    @paleo_app.command(
        name="corelle",
        context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
    )
    def _corelle(ctx: Context):
        """Run the corelle CLI"""
        corelle_cli.name = "corelle"
        corelle_cli(ctx.args)

    @paleo_app.command(name="build-plate-index")
    def _build_carto_plate_index():
        """Build a representation of the Carto map layers, split by plate polygons"""
        from .corelle import build_carto_plate_index

        db = get_db()
        build_carto_plate_index(db)

    main.add_typer(
        paleo_app,
        name="paleogeography",
        rich_help_panel="Subsystems",
        short_help="Manage paleogeography data",
    )

    def update_corelle(db):
        environ["CORELLE_DB"] = app.settings.pg_database
        print("Creating models for [bold cyan]corelle[/] subsystem")
        initialize(drop=False)
        create_corelle_fixtures(db)

    db_subsystem.register_schema_part(
        name="corelle",
        callback=update_corelle,
    )

    return app
