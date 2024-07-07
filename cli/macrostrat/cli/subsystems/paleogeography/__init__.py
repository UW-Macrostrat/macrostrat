from os import environ
from .corelle import create_corelle_fixtures, build_carto_plate_index
from ...database import get_db


def load_paleogeography_subsystem(app, main, db_subsystem):
    try:
        environ["CORELLE_DB"] = app.settings.pg_database
        from corelle.engine import cli as corelle_cli
        from corelle.engine.database import initialize

        corelle_cli.name = "corelle"
        corelle_cli.help = "Manage plate rotation models"

        main.add_click_command(
            corelle_cli,
            "corelle",
            rich_help_panel="Subsystems",
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

    except ImportError as err:
        pass

    @main.command(name="carto-plate-index")
    def _build_carto_plate_index():
        """Build a representation of the Carto map layers, split by plate polygons"""
        from .corelle import build_carto_plate_index

        db = get_db()
        build_carto_plate_index(db)

    return app
