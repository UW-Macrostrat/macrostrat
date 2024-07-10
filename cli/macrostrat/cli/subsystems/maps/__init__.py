from os import environ
from pathlib import Path
from subprocess import run

from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory
from typer import Typer

from macrostrat.core import MacrostratSubsystem
from mapboard.topology_manager import create_tables, drop_tables
from mapboard.topology_manager.commands.update import _update
from mapboard.topology_manager.database import _get_instance_params
from ...database import _engine_for_db_name
from ...database._legacy import get_db

__dir__ = Path(__file__).parent


class MapsTopologySubsystem(MacrostratSubsystem):
    """Placeholder for when this becomes a bit more formalized..."""

    name = "maps"


cli = Typer(no_args_is_help=True)

config = dict(
    data_schema="map_bounds",
    topo_schema="map_bounds_topology",
    srid=4326,
    tolerance=0.0001,
)


@cli.command("create")
def create_fixtures():
    """Create topology fixtures"""
    db = get_db()

    create_tables(db, **config)

    db.run_fixtures(__dir__ / "fixtures")


@cli.command("drop")
def clean():
    """Drop topology fixtures"""
    db = get_db()
    drop_tables(db, **config)


@cli.command("fill")
def fill():
    """Fill topology fixtures"""
    db = get_db()

    db.run_sql(__dir__ / "procedures" / "fill-topology.sql")


@cli.command("update")
def update():
    """Update topology fixtures"""
    db = get_db()
    db.instance_params = _get_instance_params(**config)
    _update(db)


@cli.command("test")
def test():
    """Test topology fixtures"""
    from macrostrat.core import app

    db_engine = _engine_for_db_name("map_topology_test")
    db_url = raw_database_url(db_engine.url)

    environ["TOPO_TESTING_DATABASE_URL"] = db_url

    srcroot = app.settings.srcroot
    topo_mgr = srcroot / "deps/topology-manager"
    with working_directory(topo_mgr):
        run(["pytest", "-s"])
