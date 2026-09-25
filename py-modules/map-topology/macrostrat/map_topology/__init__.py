from rich import print
from typer import Argument, Option, Typer

from macrostrat.core.database import get_database
from macrostrat.core.environment import WriteScope
from macrostrat.core.safety import require_write_access, writes

from .config import get_topo_manager
from .manager import (
    RETRY_TOLERANCE,
    _print_map_info,
    filter_maps,
    get_map_list,
    get_maps_with_changed_geometries,
    proc,
    release_map,
)

cli = Typer(no_args_is_help=True)


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


@cli.command("remove")
def _remove(
    maps: list[str] = Argument(None),
    yes: bool = Option(
        False, "--yes", "-y", help="Skip the confirmation prompt where one is allowed"
    ),
):
    """Remove topology fixtures"""
    mgr = get_topo_manager()
    all_maps = get_map_list(mgr.db, filter_by=maps)

    # Replaces an ad-hoc input() prompt. That prompt fired even in `local`,
    # where this needs no ceremony, and raised EOFError as a traceback when
    # there was no terminal instead of refusing cleanly. The gate is
    # class-aware and states the count, which the caller may not know when
    # `maps` is empty and every map is selected.
    require_write_access(
        WriteScope.Data,
        assume_yes=yes,
        action=f"removal of topogeometries for {len(all_maps)} map(s)",
    )

    all_map_ids = [m.map_id for m in all_maps]

    mgr.remove_maps(all_map_ids)


@cli.command("clean", rich_help_panel="Utils")
@writes(WriteScope.Data, action="topology clean")
def _clean(
    yes: bool = Option(
        False, "--yes", "-y", help="Skip the confirmation prompt where one is allowed"
    ),
):
    """Clean topology fixtures"""
    mgr = get_topo_manager()
    mgr.clean_topology()


@cli.command("rebuild", rich_help_panel="Utils")
@writes(WriteScope.Data, action="topology rebuild")
def rebuild(
    maps: list[str] = Argument(None),
    yes: bool = Option(
        False, "--yes", "-y", help="Skip the confirmation prompt where one is allowed"
    ),
):
    """Rebuild topology fixtures"""
    mgr = get_topo_manager()

    mgr.rebuild_layer_constraints()

    if maps is not None:
        all_maps = get_map_list(mgr.database, maps)
        for map in all_maps:
            _set_dirty(mgr.database, map.map_id)

    mgr.rebuild_edge_relations()


@cli.command("mark-all", rich_help_panel="Utils")
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
    _update_identity(db)


def _update_identity(db):
    db.run_query(
        """
         UPDATE map_bounds_topology.map_face
         SET map_id = map_bounds_topology.identity_for_area(geometry, map_layer)
        """
    )


def _set_dirty(db, map_id: int):
    """Force a map to be noded again from its bounds: drop its pieces and empty
    its topogeometry, which releases the primitives and marks the faces it
    covered dirty. The strongest form of dirty, and the one `topo rebuild` wants."""
    release_map(db, map_id)


@cli.command("update")
def _update(
    maps: list[str] = Argument(None),
    *,
    bulk: bool = False,
    verbose: bool = Option(
        False, "--verbose", "-v", help="List maps already noded from current bounds"
    ),
):
    """The one command after any edit to maps, bounds or compilations: node the
    maps whose bounds changed, recompile compilation bounds and priority paths,
    re-solve the faces whose owner changed, and rebuild member faces. `--bulk`
    re-nodes the selected maps from scratch."""
    mgr = get_topo_manager()
    mgr.update_full(maps, bulk=bulk, verbose=verbose)


@cli.command("summary")
def summary():
    """Summarize the topology"""
    db = get_database()
    res = db.run_query("SELECT TopologySummary('map_bounds_topology')").scalar()
    print(res)


@cli.command("errors")
def errors(maps: list[str] = Argument(None), fix: bool = False):
    """Show pieces that failed to node, per map; `--fix` retries them at the
    reduced tolerance."""
    db = get_database()

    total = db.run_query(
        "SELECT count(*) FROM map_bounds.map_topo WHERE topology_error IS NOT NULL"
    ).scalar()
    print(f"Found {total} failed pieces")
    if not fix and total > 0:
        print("Use --fix to retry them")

    rows = db.run_query(
        """
        SELECT t.id, t.source_id AS map_id, s.slug, a.area_km, t.tolerance,
               t.topology_error
        FROM map_bounds.map_topo t
        JOIN maps.sources s ON s.source_id = t.source_id
        JOIN map_bounds.map_area a ON a.source_id = t.source_id
        WHERE t.topology_error IS NOT NULL
        ORDER BY t.source_id, ST_GeoHash(t.geometry::geography)
        """
    ).all()
    if maps:
        rows = list(filter_maps(rows, maps))

    curr_map_id = None
    for row in rows:
        if curr_map_id != row.map_id:
            print()
            _print_map_info(row, prefix="Source ")
            curr_map_id = row.map_id
        err = row.topology_error
        print(f"[dim]- {row.id} (at {row.tolerance}): [/dim]", end="")
        if fix:
            err = _fix_error(db, row.map_id, row.id)
        if err is None:
            print("[green]fixed")
        else:
            print(f"[dim red]{err}")

    if fix:
        n = db.run_query(
            "SELECT map_bounds_topology.rebuild_dirty_edge_relations()"
        ).scalar()
        db.session.commit()
        if n:
            print(f"[dim]Rebuilt edge relations for {n} topogeometries")


def _fix_error(db, map_id: int, piece_id: int, tolerance: float = RETRY_TOLERANCE):
    """Retry one failed piece at the reduced tolerance. Returns None on success,
    or the error text."""
    err = db.run_query(
        """
        WITH outcome AS (
          SELECT map_bounds_topology.update_boundary_topo(l, t.geometry, CAST(:tolerance AS numeric)) AS err
          FROM map_bounds.map_topo t
          JOIN map_bounds.map_area l ON l.id = t.source_id
          WHERE t.id = :id AND t.source_id = :map_id
        )
        UPDATE map_bounds.map_topo t
        SET noded = (o.err IS NULL), topology_error = o.err, tolerance = :tolerance
        FROM outcome o
        WHERE t.id = :id
        RETURNING o.err
        """,
        dict(id=piece_id, map_id=map_id, tolerance=tolerance),
    ).scalar()
    db.session.commit()
    return err
