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
def update(
    *maps: list[int],
    remove: bool = False,
):
    """Update topology fixtures"""
    db = get_db()

    # Get a list of maps ordered from large to small

    all_maps = db.run_query(
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

    if maps is not None and len(maps) > 0:
        all_maps = [m for m in all_maps if m.source_id in maps]

    if remove:
        # Check with the user
        res = input(f"Remove existing topogeometries for {len(all_maps)} maps? [y/N] ")
        if res.lower() not in ["y", "yes"]:
            return

    start_time = time.time()
    for map in all_maps:
        process_map(db, map, remove=remove)

    fix_errors(db)

    end_time = time.time()

    print(f"Total time: {end_time - start_time:.3f} seconds")


def _print_source_info(map, prefix="Processing map "):
    print(
        f"{prefix}[bold green]{map.slug}[/][dim] - #[bold gray]{map.source_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
    )


def process_map(db, map, remove=False):
    _print_source_info(map, prefix="Processing map ")
    if remove:
        print("Removing existing map topo elements")
        remove_map_topo_elements(db, map.source_id)

    prepare_map_topo_features(db, map.source_id)
    print()
    add_topogeometries(db, map.source_id)
    print()
    print()


def prepare_map_topo_features(db, source_id: int):
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


def remove_map_topo_elements(db, source_id: int):
    res = db.run_query(
        """
        DELETE FROM map_bounds.map_topo
        WHERE source_id = :source_id
        RETURNING id
        """,
        dict(source_id=source_id),
    ).scalars()
    print("Removed {len(res)} map_topo elements")

    # Clean up topogeoms
    res = db.run_query(
        """
        SELECT topology.RemoveUnusedPrimitives('map_bounds_topology', geometry::box2d)
        FROM map_bounds.map_area
        WHERE source_id = :source_id
        """,
        dict(source_id=source_id),
    ).scalar()

    print(f"Removed {res} orphaned topology elements")

    db.session.commit()


def _do_update(db, source_id: int):
    t_start = time.time()

    batch_size = 100
    tolerance = 0.0001

    res = db.run_query(
        proc("update-topology-row"),
        dict(source_id=source_id, batch_size=batch_size, tolerance=tolerance),
    ).one()

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


@cli.command("errors")
def errors(fix: bool = False):
    """Show topology errors"""
    db = get_db()

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

    if not fix and res > 0:
        print("Use --fix to attempt to fix them")

    if fix:
        print("Cleaning topology")
        db.run_sql(
            "SELECT RemoveUnusedPrimitives('map_bounds_topology', :bbox);",
            dict(bbox=None),
        )

    # Try to re-run errors
    res = db.run_query(
        """
        SELECT t.id, t.source_id, slug, area_km, t.topology_error
        FROM map_bounds.map_topo t
        JOIN maps.sources_metadata
        USING (source_id)
        JOIN map_bounds.map_area
        USING (source_id)
        WHERE t.topology_error IS NOT NULL
        ORDER BY t.source_id
    """
    )

    curr_source_id = None
    for row in res:
        if curr_source_id != row.source_id:
            print()
            _print_source_info(row, prefix="Source ")
            curr_source_id = row.source_id
        err = row.topology_error

        print(f"[dim]- {row.id}: [/dim]", end="")
        if fix:
            res = _fix_error(row.id)
            err = res

        if err is None:
            print(f"[green]fixed")
        else:
            print(f"[dim red]{err}")


def _fix_error(id: int):
    db = get_db()
    res = db.run_query(
        """
          SELECT
            map_bounds.update_topogeom(m) res
          FROM map_bounds.map_topo m
          WHERE topo IS NULL
            AND topology_error IS NOT NULL
            AND id = :id
        """,
        dict(id=id),
    ).scalar()
    db.session.commit()
    return res


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
