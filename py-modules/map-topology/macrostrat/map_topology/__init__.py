import time
from dataclasses import dataclass
from os import environ
from pathlib import Path
from subprocess import run

import typer
from mapboard.topology_manager import TopologyManager
from mapboard.topology_manager.config import (
    IdentityStrategy,
    TopologyContext,
    create_context,
)
from rich import print
from typer import Argument, Typer

from macrostrat.core.database import get_database
from macrostrat.database import Database
from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory

__dir__ = Path(__file__).parent


cli = Typer(no_args_is_help=True)

config = dict(
    data_schema="map_bounds",
    topo_schema="map_bounds_topology",
    srid=4326,
    tolerance=0.0001,
)


proc = lambda name: __dir__ / "procedures" / f"{name}.sql"


IDENTITY_STRATEGY = IdentityStrategy(
    identity_column="map_id",
    install=lambda ctx: ctx.database.run_fixtures(
        __dir__ / "fixtures" / "03-identity-management.sql"
    ),
)


def create_topo_context(db: Database):
    return create_context(
        db,
        data_schema="map_bounds",
        topo_schema="map_bounds_topology",
        srid=4326,
        tolerance=0.0001,
        identity_strategy=IDENTITY_STRATEGY,
        boundary_table="map_area",
        create_data_tables=lambda ctx: db.run_fixtures(
            __dir__ / "fixtures" / "01-create-tables.sql"
        ),
        notify_triggers=False,
    )


def get_topo_manager():
    db = get_database()
    return TopologyManager(create_topo_context(db))


def get_topo_context():
    return get_topo_manager().context


def create_topo_fixtures(ctx: TopologyContext, reset: bool = False):
    db = ctx.database
    if reset:
        db.run_fixtures(proc("drop-tables"))

    mgr = TopologyManager(ctx)
    mgr.create_tables()


@cli.command("create")
def _create_fixtures(reset: bool = False):
    """Create topology fixtures"""
    mgr = get_topo_manager()
    mgr.create_tables()


@cli.command("drop")
def drop():
    """Drop topology fixtures"""
    mgr = get_topo_manager()
    mgr.database.run_fixtures(proc("drop-tables"))


@cli.command("reset")
def reset():
    """Reset topogeometry creation"""
    ctx = get_topo_context()
    ctx.database.run_fixtures(proc("reset-topology"))


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
        if m.map_id in ids or m.slug in slugs:
            yield m


@cli.command("remove")
def _remove(maps: list[str] = Argument(None)):
    """Remove topology fixtures"""
    mgr = get_topo_manager()
    db = mgr.database

    # Get a list of maps ordered from large to small
    all_maps = get_map_list(db, filter_by=maps)

    # Check with the user
    res = input(f"Remove existing topogeometries for {len(all_maps)} maps? [y/N] ")
    if res.lower() not in ["y", "yes"]:
        raise Exception("User aborted")

    for _map in all_maps:
        _print_map_info(_map, prefix="Removing map ")
        print("Removing existing map topo elements")
        _remove_map_topo_elements(db, _map.map_id)

    _clean(mgr)


def _clean(mgr: TopologyManager):
    res = mgr.db.run_query(proc("clear-extra-topogeometries")).scalar()
    mgr.db.session.commit()
    print(f"Removed {res} orphaned [cyan]map_topo[/cyan] topogeometries")
    mgr.clean_topology()


@cli.command("clean")
def clean():
    """Clean topology fixtures"""
    _clean(get_topo_context())


@cli.command("rebuild")
def rebuild():
    """Rebuild topology fixtures"""
    mgr = get_topo_manager()
    mgr.create_tables()
    mgr.rebuild_edge_relations()


@cli.command("update")
def update(
    maps: list[str] = Argument(None),
    *,
    remove: bool = False,
):
    """Update topology fixtures"""
    mgr = get_topo_manager()
    update_maps(mgr.ctx, maps, remove=remove)
    mgr.update(incremental=True, composite_layers=True)


def update_maps(
    ctx: TopologyContext,
    maps: list[str] = None,
    *,
    remove: bool = False,
    clean: bool = True,
    **kwargs,
):
    db = ctx.database
    # Copy all maps into the schema
    db.run_sql(proc("copy-all-maps"))

    # Associate maps with compilations
    db.run_sql(proc("set-map-priority"))

    # Get a list of maps ordered from large to small
    all_maps = get_map_list(db, maps)

    if remove:
        _remove(maps)

    start_time = time.time()
    for _map in all_maps:
        process_map(db, _map, **kwargs)

    if clean:
        mgr = TopologyManager(ctx)
        _clean(mgr)

    end_time = time.time()

    print(f"Total time: {end_time - start_time:.3f} seconds")


def get_map_list(db, filter_by: list[str] = None):
    all_maps = db.run_query(
        """
        SELECT
            a.id map_id,
            slug,
            scale,
            area_km
        FROM map_bounds.map_area a
        JOIN maps.sources s
          ON a.id = s.source_id
        ORDER BY area_km DESC
    """
    ).all()
    if filter_by is not None:
        all_maps = list(filter_maps(all_maps, filter_by))
    return all_maps


def _print_map_info(map, prefix="Processing map "):
    print(
        f"{prefix}[bold green]{map.slug}[/][dim] - #[bold gray]{map.map_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
    )


def process_map(db, map, **kwargs):
    _print_map_info(map, prefix="Processing map ")

    prepare_map_topo_features(db, map, **kwargs)
    print()
    add_topogeometries(db, map.map_id)
    print()
    print()


def prepare_map_topo_features(db, _map, *, subdivide_vertices: int = 256):
    """
    The map_topo update loop allows large/complex map_area features to be written and error-checked incrementally.
    This dramatically speeds up initial insertion of certain maps into the topology tables.
    """

    map_id = _map.map_id
    simplify_amount = 0.0001
    # Don't simplify the boundaries of fine-scale maps as much.
    if _map.scale == "large":
        simplify_amount = 0.00001

    t_start = time.time()
    res = db.run_query(
        proc("insert-map-topo-features"),
        dict(
            map_id=map_id,
            simplify_amount=simplify_amount,
            subdivide_vertices=subdivide_vertices,
        ),
    ).one()
    db.session.commit()
    elapsed = time.time() - t_start
    total = res.inserted + res.existing
    if res.inserted > 0:
        print(f"Processing {total} [cyan]map_topo[/cyan] features")
        print(f"  inserted: {res.inserted}, existing: {res.existing}")
    print(f"{total} features,  {elapsed:.3f} seconds")


def _remove_map_topo_elements(db, map_id: int):
    res = list(
        db.run_query(
            """
        DELETE FROM map_bounds.map_topo
        WHERE map_id = :map_id
        RETURNING id
        """,
            dict(map_id=map_id),
        )
    )
    db.session.commit()
    print(f"Removed {len(res)} map_topo elements")


@dataclass
class TopoUpdateResult:
    updated: int
    failed: int
    remaining: int
    errors: list[str] | None


def _do_update(db, map_id: int) -> TopoUpdateResult:
    t_start = time.time()

    batch_size = 100
    tolerance = 0.0001

    res = db.run_query(
        proc("update-topology-row"),
        dict(map_id=map_id, batch_size=batch_size, tolerance=tolerance),
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
    return TopoUpdateResult(
        updated=res.updated,
        failed=res.failed,
        remaining=res.remaining,
        errors=res.errors,
    )


def _retry_errors(db, map_id: int, tolerance: float) -> int:
    """Re-attempt this map's errored map_topo rows at the given snap tolerance,
    in batches, until a pass recovers nothing more. Returns the number of rows
    recovered. Rows that still fail keep their topology_error for inspection."""
    recovered = 0
    while True:
        res = db.run_query(
            proc("update-topology-fix-errors"),
            dict(map_id=map_id, batch_size=100, tolerance=tolerance),
        ).one()
        db.session.commit()
        if not res.updated:
            break
        recovered += res.updated
    return recovered


def add_topogeometries(db, map_id: int) -> TopoUpdateResult:
    n_remaining = 1000
    niter = 0
    updated = 0
    failed = 0
    errors = []
    while n_remaining > 0:
        res = _do_update(
            db,
            map_id,
        )
        n_remaining = res.remaining

        updated += res.updated
        failed += res.failed
        if res.errors is not None and len(res.errors) > 0:
            errors.extend(res.errors)

        niter += 1

    # Re-attempt insertion failures at a snap tolerance just below the global
    # 0.0001 default. The default over-snaps some incoming geometry into
    # insertion failures (curve-not-simple, crosses-edge); a slightly smaller
    # tolerance recovers a meaningful fraction without the spurious snapping a
    # larger tolerance introduces. (Exact/0 and densification don't help here.)
    recovered = _retry_errors(db, map_id, tolerance=0.00001)
    if recovered > 0:
        updated += recovered
        print(f"  Recovered {recovered} errored features at reduced tolerance")

    has_valid_topogeom_or_error = db.run_query(
        """
        SELECT EXISTS (
        SELECT 1 FROM map_bounds.map_area
        WHERE id = :map_id
          AND  ( topo IS NOT NULL OR topology_error IS NOT NULL) -- existing topogeometry
          AND (geometry_hash IS NOT NULL AND geometry_hash = md5(ST_AsBinary(geometry)::uuid)) -- geometry matches hash
        )
        """,
        dict(map_id=map_id),
    ).scalar()

    if updated > 0 or not has_valid_topogeom_or_error:
        # We need to create the topology
        print("  Updating map_area topogeometry")
        db.run_query(proc("create-source-topogeometry"), dict(map_id=map_id))
        db.session.commit()
    else:
        print("[dim]  No topogeometries to add")

    # Edge-relation maintenance for face-based topogeometries is deferred (the
    # trigger only marks dirty), so rebuild the affected relations now that all
    # of this map's features and its map_area topogeometry are in place.
    n = db.run_query(
        "SELECT map_bounds_topology.rebuild_dirty_edge_relations()"
    ).scalar()
    db.session.commit()
    if n and n > 0:
        print(f"  Rebuilt edge relations for {n} topogeometries")

    return TopoUpdateResult(updated, failed, 0, errors)


@cli.command("summary")
def summary():
    """Summarize the topology"""
    db = get_database()
    res = db.run_query("SELECT TopologySummary('map_bounds_topology');").scalar()
    print(res)


@cli.command("errors")
def errors(maps: list[str] = Argument(None), fix: bool = False):
    """Show topology errors"""
    db = get_database()

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
            "SELECT topology.RemoveUnusedPrimitives('map_bounds_topology', :bbox);",
            dict(bbox=None),
        ).scalar()
        print(f"Removed {res} orphaned topology elements")
        db.session.commit()

    # Try to re-run errors
    all_maps = db.run_query(
        """
        SELECT t.id, t.map_id, slug, area_km, t.topology_error
        FROM map_bounds.map_topo t
        JOIN maps.sources_metadata m
          ON t.map_id = m.source_id
        JOIN map_bounds.map_area
        USING (map_id)
        WHERE t.topology_error IS NOT NULL
        ORDER BY t.map_id, ST_GeoHash(t.geometry::geography)
    """
    ).all()

    if maps is not None and len(maps) > 0:
        all_maps = list(filter_maps(all_maps, maps))

    curr_map_id = None
    for row in all_maps:
        if curr_map_id != row.map_id:
            print()
            _print_map_info(row, prefix="Source ")
            curr_map_id = row.map_id
        err = row.topology_error

        print(f"[dim]- {row.id}: [/dim]", end="")
        if fix:
            res = _fix_error(row.id)
            err = res

        if err is None:
            print(f"[green]fixed")
        else:
            print(f"[dim red]{err}")

    if fix:
        # The deferred edge-relation trigger only marked rows dirty; rebuild the
        # affected relations now that the retries are done.
        n = db.run_query(
            "SELECT map_bounds_topology.rebuild_dirty_edge_relations()"
        ).scalar()
        db.session.commit()
        if n:
            print(f"[dim]Rebuilt edge relations for {n} topogeometries")


def _fix_error(id: int, tolerance: float = 0.00001):
    """Re-attempt a single errored map_topo row at a reduced snap tolerance
    (below the 1e-4 global default). Empirically this recovers a meaningful
    share of insertion-snapping failures (curve-not-simple, crosses-edge);
    increasing tolerance or densifying does not. Returns None on success, or
    the error text on failure."""
    db = get_database()
    err = db.run_query(
        """
          SELECT map_bounds.update_topogeom(m, :tolerance) res
          FROM map_bounds.map_topo m
          WHERE topo IS NULL
            AND topology_error IS NOT NULL
            AND id = :id
        """,
        dict(id=id, tolerance=tolerance),
    ).scalar()
    db.session.commit()
    return err


@cli.command(
    "test", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def test(ctx: typer.Context):
    """Test topology fixtures"""
    from macrostrat.core import app

    db_url = raw_database_url(
        get_database().engine.url.set(database="map_topology_test")
    )

    environ["TOPO_TESTING_DATABASE_URL"] = db_url

    srcroot = app.settings.srcroot
    topo_mgr = srcroot / "submodules/topology-manager"
    with working_directory(topo_mgr):
        run(["pytest", *ctx.args])
