import time
from os import environ
from pathlib import Path
from subprocess import run

from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory
from rich import print
from typer import Typer, Argument

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


def split_ids_and_slugs(map_ids):
    ids = []
    slugs = []
    for m in map_ids:
        try:
            ids.append(int(m))
        except ValueError:
            slugs.append(m)
    return ids, slugs


def filter_maps(all_maps, map_ids: list[str]):
    ids, slugs = split_ids_and_slugs(map_ids)
    for m in all_maps:
        if m.source_id in ids or m.slug in slugs:
            yield m


@cli.command("remove")
def _remove(maps: list[str] = Argument(None)):
    """Remove topology fixtures"""
    db = get_db()

    # Get a list of maps ordered from large to small
    all_maps = get_map_list(db, filter_by=maps)

    # Check with the user
    res = input(f"Remove existing topogeometries for {len(all_maps)} maps? [y/N] ")
    if res.lower() not in ["y", "yes"]:
        raise Exception("User aborted")

    for _map in all_maps:
        _print_source_info(_map, prefix="Removing map ")
        print("Removing existing map topo elements")
        _remove_map_topo_elements(db, _map.source_id)

    _clean(db)


def _clean(db):
    res = db.run_query(proc("clear-extra-topogeometries")).scalar()
    db.session.commit()
    print(f"Removed {res} orphaned [cyan]map_topo[/cyan] topogeometries")

    res = db.run_query(
        """
        SELECT topology.RemoveUnusedPrimitives('map_bounds_topology', null)
        """,
    ).scalar()
    db.session.commit()
    print(f"Removed {res} orphaned topology primitives")


@cli.command("clean")
def clean():
    """Clean topology fixtures"""
    db = get_db()
    _clean(db)


@cli.command("update")
def update(
    maps: list[str] = Argument(None),
    *,
    remove: bool = False,
):
    """Update topology fixtures"""
    db = get_db()

    # Get a list of maps ordered from large to small
    all_maps = get_map_list(db, maps)

    if remove:
        _remove(maps)

    start_time = time.time()
    for _map in all_maps:
        process_map(db, _map)

    _clean(db)

    end_time = time.time()

    print(f"Total time: {end_time - start_time:.3f} seconds")


def get_map_list(db, filter_by: list[str] = None):
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
    if filter_by is not None:
        all_maps = list(filter_maps(all_maps, filter_by))
    return all_maps


def _print_source_info(map, prefix="Processing map "):
    print(
        f"{prefix}[bold green]{map.slug}[/][dim] - #[bold gray]{map.source_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
    )


def process_map(db, map):
    _print_source_info(map, prefix="Processing map ")

    prepare_map_topo_features(db, map)
    print()
    add_topogeometries(db, map.source_id)
    print()
    print()


def prepare_map_topo_features(db, _map):
    # Insert or update the map topo

    source_id = _map.source_id
    simplify_amount = 0.0001
    # Don't simplify the boundaries of fine-scale maps as much.
    if _map.scale == "large":
        simplify_amount = 0.00001

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
                a.source_id,
                -- We have to remove snapping behavior to make sure that the geometry is valid.
                ST_Subdivide(
                    ST_MakeValid(
                        ST_SimplifyPreserveTopology(
                            ST_Multi(a.geometry),
                            :simplify_amount
                        )
                    ),
                    256,
                    0.0001
                )
            FROM map_bounds.map_area a
            JOIN maps.sources_metadata m
              ON a.source_id = :source_id
            WHERE a.source_id = :source_id
              AND (SELECT n FROM existing_count) = 0
            RETURNING id, source_id
        )
        SELECT count(*) as inserted, (SELECT n FROM existing_count) as existing
        FROM ins
        """,
        dict(source_id=source_id, simplify_amount=simplify_amount),
    ).one()
    db.session.commit()
    elapsed = time.time() - t_start
    total = res.inserted + res.existing
    print(f"Processing {total} [cyan]map_topo[/cyan] features")
    print(f"  inserted: {res.inserted}, existing: {res.existing}")
    print(f"  {elapsed:.3f} seconds")


def _remove_map_topo_elements(db, source_id: int):
    res = list(
        db.run_query(
            """
        DELETE FROM map_bounds.map_topo
        WHERE source_id = :source_id
        RETURNING id
        """,
            dict(source_id=source_id),
        )
    )
    db.session.commit()
    print(f"Removed {len(res)} map_topo elements")


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


@cli.command("summary")
def summary():
    db = get_db()
    res = db.run_query("SELECT TopologySummary('map_bounds_topology');").scalar()
    print(res)


@cli.command("errors")
def errors(maps: list[str] = Argument(None), fix: bool = False):
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
        res = db.run_query(
            "SELECT RemoveUnusedPrimitives('map_bounds_topology', :bbox);",
            dict(bbox=None),
        ).scalar()
        print(f"Removed {res} orphaned topology elements")
        db.session.commit()

    # Try to re-run errors
    all_maps = db.run_query(
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
    ).all()

    if maps is not None and len(maps) > 0:
        all_maps = list(filter_maps(all_maps, maps))

    curr_source_id = None
    for row in all_maps:
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
    densify: int = 1
    err = "Unknown error"
    while err is not None and densify <= 100:
        if densify > 1:
            print(f"  Densifying by {densify}")
        err = db.run_query(
            """
              SELECT
                map_bounds.update_topogeom(m, :tolerance, :densify) res
              FROM map_bounds.map_topo m
              WHERE topo IS NULL
                AND topology_error IS NOT NULL
                AND id = :id
            """,
            dict(id=id, densify=densify * 10, tolerance=0.0001 * densify),
        ).scalar()
        densify *= 10
    db.session.commit()
    return err


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
