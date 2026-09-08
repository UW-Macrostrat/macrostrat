from os import environ

from typer import Context, Typer

from ...database import get_db
from .corelle import build_carto_plate_index, create_corelle_fixtures


class SubsystemLoadError(Exception):
    pass


def _corelle_url(app) -> str:
    """The database URL for corelle, for this invocation's role. Resolves."""
    from macrostrat.core.database import current_database_role

    return app.settings.database_url(current_database_role()).render_as_string(
        hide_password=False
    )


def build_paleogeography_subsystem(app, db_subsystem):
    from importlib.util import find_spec

    from macrostrat.core.connections import DatabaseRole

    conn = app.settings.database_connection()
    if conn is None:
        raise SubsystemLoadError("No database configured, skipping corelle subsystem")

    try:
        available = find_spec("corelle.engine") is not None
    except ImportError:
        # find_spec imports the parent package; an absent `corelle` raises.
        available = False
    if not available:
        raise SubsystemLoadError("Corelle subsystem not available")

    # corelle reads CORELLE_DB when `corelle.engine.database` is imported. A
    # literal config exports it now, as before; a config whose credential lives
    # in a secret manager must not be fetched at CLI import, so the export and
    # the import both wait for command time (see `_corelle_url`).
    if not conn.requires_resolution(DatabaseRole.Writer):
        environ["CORELLE_DB"] = conn.url(DatabaseRole.Writer).render_as_string(
            hide_password=False
        )

    paleo_app = Typer(
        name="paleogeography",
        no_args_is_help=True,
        short_help="Paleogeography models and data",
    )

    @paleo_app.command(
        name="corelle",
        context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
    )
    def _corelle(ctx: Context):
        """Run the corelle CLI"""
        environ["CORELLE_DB"] = _corelle_url(app)
        from corelle.engine import cli as corelle_cli

        corelle_cli.name = "corelle"
        corelle_cli(ctx.args)

    @paleo_app.command(name="build-plate-index")
    def _build_carto_plate_index():
        """Build a representation of the Carto map layers, split by plate polygons"""
        from .corelle import build_carto_plate_index

        db = get_db()
        build_carto_plate_index(db)

    def update_corelle(db):
        environ["CORELLE_DB"] = _corelle_url(app)
        from corelle.engine.database import initialize

        print("Creating models for [bold cyan]corelle[/] subsystem")
        initialize(drop=False)
        create_corelle_fixtures(db)

    db_subsystem.register_schema_part(
        name="corelle",
        callback=update_corelle,
    )

    return paleo_app
