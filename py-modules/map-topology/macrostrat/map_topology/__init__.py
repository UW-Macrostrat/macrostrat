from os import environ
from pathlib import Path
from subprocess import run

import typer
from mapboard.topology_manager import TopologyManager
from mapboard.topology_manager.config import TopologyContext
from rich import print
from typer import Argument, Typer

from macrostrat.core.database import get_database
from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import working_directory

from .config import create_topo_context, get_topo_context, get_topo_manager
from .manager import (
    _print_map_info,
    _remove_map_topo_elements,
    filter_maps,
    get_map_list,
    get_maps_with_changed_geometries,
    proc,
)

cli = Typer(no_args_is_help=True)


def create_topo_fixtures(ctx: TopologyContext, reset: bool = False):
    db = ctx.database
    if reset:
        db.run_fixtures(proc("drop-tables"))

    mgr = TopologyManager(ctx)
    mgr.create_tables()


@cli.command("status")
def status():
    """Show the current status of the topology"""
    mgr = get_topo_manager()
    res = get_maps_with_changed_geometries(mgr)
    if len(res) == 0:
        print("No maps with geometry changes")
        return
    print(f"Found {len(res)} maps with with geometry changes")
    for row in res:
        _print_map_info(row)


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


@cli.command("remove")
def _remove(maps: list[str] = Argument(None)):
    """Remove topology fixtures"""
    mgr = get_topo_manager()
    all_maps = get_map_list(mgr.db, filter_by=maps)

    # Check with the user
    res = input(f"Remove existing topogeometries for {len(all_maps)} maps? [y/N] ")
    if res.lower() not in ["y", "yes"]:
        raise Exception("User aborted")

    all_map_ids = [m.map_id for m in all_maps]

    mgr.remove_maps(all_map_ids)


@cli.command("clean")
def _clean():
    """Clean topology fixtures"""
    mgr = get_topo_manager()
    mgr.clean_topology()


@cli.command("rebuild")
def rebuild(maps: list[str] = Argument(None)):
    """Rebuild topology fixtures"""
    mgr = get_topo_manager()

    if maps is not None:
        all_maps = get_map_list(mgr.database, maps)
        for map in all_maps:
            _set_dirty(mgr.database, map.map_id)

    mgr.rebuild_edge_relations()


@cli.command("mark-all")
def mark_all():
    """Mark all map faces as dirty"""
    mgr = get_topo_manager()
    res = mgr.database.run_query(
        """
        WITH insert AS (
            INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
                SELECT f.face_id, ml.id
                FROM map_bounds_topology.face f
                CROSS JOIN map_bounds.map_layer ml
                WHERE ml.composited_from IS NULL
                ON CONFLICT DO NOTHING
                RETURNING id
        )
        SELECT count(*) FROM insert;
        """
    ).scalar()
    mgr.database.session.commit()

    print(f"Marked {res} dirty faces")


@cli.command("identify", rich_help_panel="Utils")
def update_identity():
    """Refresh the identity of all map faces"""
    mgr = get_topo_manager()
    db = mgr.database
    db.run_query(
        """
         UPDATE map_bounds_topology.map_face
         SET map_id = map_bounds_topology.identity_for_area(geometry, map_layer)
        """
    )


def _set_dirty(db, map_id: int):
    db.run_query(
        "UPDATE map_bounds.map_area SET geometry_hash = NULL WHERE id = :id",
        dict(id=map_id),
    )

    # db.run_query(
    #     """
    #  INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
    #  SELECT (topology.gettopogeomelements(topo))[1] eid, ma.map_layer
    #  FROM map_bounds.map_area ma
    #  WHERE id = :map_id
    #  ON CONFLICT DO NOTHING;
    #  """,
    #     dict(map_id=map_id),
    # )
    #


@cli.command("update")
def _update(
    maps: list[str] = Argument(None),
    *,
    bulk: bool = False,
    remove: bool = False,
):
    """Update topology fixtures"""
    mgr = get_topo_manager()
    mgr.update_full(maps, bulk=bulk, remove=remove)


@cli.command("summary")
def summary():
    """Summarize the topology"""
    db = get_database()
    res = db.run_query("SELECT TopologySummary('map_bounds_topology')").scalar()
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
          ON t.map_id = map_area.id
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
