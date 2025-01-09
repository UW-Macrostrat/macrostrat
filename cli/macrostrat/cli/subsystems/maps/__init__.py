import time
from os import environ
from pathlib import Path
from subprocess import run

from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory
from rich import print
from typer import Typer

from macrostrat.core import MacrostratSubsystem
from ...database._legacy import get_db
from ...database.utils import engine_for_db_name

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


proc = lambda name: __dir__ / "procedures" / f"{name}.sql"


@cli.command("create")
def create_fixtures(reset: bool = False):
    """Create topology fixtures"""
    db = get_db()

    if reset:
        drop()

    db.run_fixtures(__dir__ / "fixtures")


@cli.command("drop")
def drop():
    """Drop topology fixtures"""
    db = get_db()
    db.run_fixtures(proc("drop-tables"))


@cli.command("reset")
def reset():
    """Reset topogeometry creation"""
    db = get_db()
    db.run_fixtures(proc("reset-topology"))


@cli.command("update")
def update():
    """Update topology fixtures"""
    db = get_db()

    # Get a list of maps ordered from large to small

    maps = db.run_query(
        """
        SELECT
            a.source_id,
            slug,
            scale,
            area_km
        FROM map_bounds.map_area a
        JOIN maps.sources s
        USING (source_id)
        ORDER BY area_km DESC
    """
    ).all()

    start_time = time.time()
    for map in maps:
        print(
            f"Processing map [bold green]{map.slug}[/][dim] - #[bold gray]{map.source_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
        )
        process_map(db, map.source_id)
        print()
        add_topogeometries(db, map.source_id)
        print()
        print()

    fix_errors(db)

    end_time = time.time()

    print(f"Total time: {end_time - start_time:.3f} seconds")


def process_map(db, source_id: int):
    # Insert or update the map topo

    t_start = time.time()
    res = db.run_query(
        """
        WITH existing_count AS (
            SELECT COUNT(*) as n
            FROM map_bounds.map_topo
            WHERE source_id = :source_id
        ), ins AS (
            INSERT INTO map_bounds.map_topo (source_id, geometry)
            SELECT
                source_id,
                ST_Subdivide(ST_MakeValid(ST_SnapToGrid(geometry, 0.0001)), 256, 0.0001)
            FROM map_bounds.map_area
            WHERE source_id = :source_id
              AND (SELECT n FROM existing_count) = 0
            RETURNING id, source_id
        )
        SELECT count(*) as inserted, (SELECT n FROM existing_count) as existing
        FROM ins
        """,
        dict(source_id=source_id),
    ).one()
    db.session.commit()
    elapsed = time.time() - t_start
    total = res.inserted + res.existing
    print(f"Processing {total} [cyan]map_topo[/cyan] features")
    print(f"  inserted: {res.inserted}, existing: {res.existing}")
    print(f"  {elapsed:.3f} seconds")


def _run_update(db, source_id: int, *, batch_size: int = 10, tolerance: float = 0.0001):
    res = db.run_query(
        proc("update-topology-row"),
        dict(source_id=source_id, batch_size=batch_size, tolerance=tolerance),
    ).one()
    return res


def _do_update(db, source_id: int):
    t_start = time.time()

    batch_size = 100
    tolerance = 0.0001

    res = _run_update(db, source_id, batch_size=batch_size, tolerance=tolerance)

    db.session.commit()
    elapsed = time.time() - t_start
    print(
        f"  Processed {res.updated} topogeoms, {res.remaining} remaining, {elapsed:.3f} seconds"
    )
    if res.errors is not None and len(res.errors) > 0:
        print("  Errors:")
        for err in res.errors:
            print(f"   [dim]- [red]{err}")
    return res.remaining


def add_topogeometries(db, source_id: int):
    n_remaining = 1000
    while n_remaining > 0:
        n_remaining = _do_update(
            db,
            source_id,
        )


@cli.command("fix-errors")
def fix_errors():
    """Fix topology errors"""
    db = get_db()
    # Clean topology

    # Get and fix errors
    res = db.run_query(
        """
        SELECT
            count(*)
        FROM map_bounds.map_topo
        WHERE topology_error IS NOT NULL
    """
    ).scalar()

    print(f"Found {res} errors")

    print("Cleaning topology")
    db.run_sql(
        "SELECT RemoveUnusedPrimitives('map_bounds_topology', :bbox);", dict(bbox=None)
    )

    # Try to re-run errors
    res = db.run_query(
        """
        SELECT id, source_id
        FROM map_bounds.map_topo
        WHERE topology_error IS NOT NULL
        ORDER BY source_id
    """
    )

    for row in res:
        print(f"[dim]- {row.id} (source #{row.source_id}): ", end="")
        res = db.run_query(
            """
              SELECT
                map_bounds.update_topogeom(m) res
              FROM map_bounds.map_topo m
              WHERE topo IS NULL
                AND topology_error IS NOT NULL
                AND id = :id
            """,
            dict(id=row.id),
        ).scalar()
        db.session.commit()

        if res is None:
            print(f"[dim green]fixed")
        else:
            print(f"[dim red]{res}")


@cli.command("test")
def test():
    """Test topology fixtures"""
    from macrostrat.core import app

    db_engine = engine_for_db_name("map_topology_test")
    db_url = raw_database_url(db_engine.url)

    environ["TOPO_TESTING_DATABASE_URL"] = db_url

    srcroot = app.settings.srcroot
    topo_mgr = srcroot / "deps/topology-manager"
    with working_directory(topo_mgr):
        run(["pytest", "-s"])
