import time

from rich import print
from typer import Argument, Option, Typer

from macrostrat.core.database import get_database
from macrostrat.core.environment import WriteScope
from macrostrat.core.safety import require_write_access, writes

from .check import MAX_VALIDATE_SPAN
from .config import get_topo_manager
from .grid import drop_grid, node_grid, retry_grid, seed_grid
from .manager import (
    RETRY_TOLERANCE,
    _duration,
    _print_map_info,
    filter_maps,
    get_held_maps,
    get_map_list,
    get_maps_with_changed_geometries,
    proc,
    release_map,
    vacuum_topology,
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
    # Every map holding topology, including ones no longer noded.
    all_maps = get_held_maps(mgr.db, filter_by=maps)

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
    vacuum: bool = Option(
        False,
        "--vacuum",
        help="Then compact the primitive tables noding has rewritten (VACUUM FULL)",
    ),
):
    """Clean topology fixtures"""
    mgr = get_topo_manager()
    mgr.clean_topology()
    if vacuum:
        vacuum_topology(mgr.database)


@cli.command("grid", rich_help_panel="Utils")
@writes(WriteScope.Data, action="topology grid")
def _grid(
    extent: str = Option(
        None,
        help="Only segments touching this lon/lat box, as xmin,ymin,xmax,ymax; the"
        " whole world otherwise",
    ),
    retry: bool = Option(
        False,
        "--retry",
        help="Make failed lines pending again first, restoring split lines whose"
        " pieces never noded",
    ),
    drop: bool = Option(
        False,
        "--drop",
        help="Instead take the whole grid out of the topology and reset it to be"
        " seeded again; re-solve with `topo update` before re-gridding",
    ),
):
    """Seed the lon/lat grid and node its pending segments, so no face spans
    the globe. The first run on a populated topology is slow: it splits the
    largest faces, 90° lines first. Do not run it while `topo update` is noding;
    `--retry` recovers a run that was."""
    from mapboard.topology_manager.commands.edge_relations import (
        validate_edge_relations,
    )

    mgr = get_topo_manager()
    db = mgr.database
    if drop:
        if retry or extent is not None:
            raise ValueError("--drop takes neither --retry nor --extent")
        res = drop_grid(db)
        print(
            f"[green]{res['removed']}[/] primitives removed,"
            f" [green]{res['mbrs_fixed']}[/] face bounding boxes fixed"
        )
        for x, y, err in res["failed_cells"]:
            print(f"  [red]cell {x:g},{y:g} not cleaned:[/] {err}")
        for face_id, err in res["failed_faces"]:
            print(f"  [red]face {face_id} not fixed:[/] {err}")
        return
    box = None
    if extent is not None:
        box = tuple(float(v) for v in extent.split(","))
        if len(box) != 4:
            raise ValueError("--extent takes four numbers: xmin,ymin,xmax,ymax")
    if retry:
        restored, dropped, cleared = retry_grid(db)
        print(
            f"[green]{restored}[/] split lines restored whole ({dropped} pieces"
            f" dropped), [green]{cleared}[/] failures cleared"
        )
    seeded = seed_grid(db, extent=box)
    print(f"[green]{seeded}[/] grid segments added")
    t0 = time.time()
    noded, failed = node_grid(db)
    print(
        f"[green]{noded}[/] noded, [red]{failed}[/] failed in {_duration(time.time() - t0)}"
    )
    report = validate_edge_relations(mgr.ctx)
    if not report.in_sync:
        print(
            f"[red]barrier rows out of sync: {report.missing} missing, {report.extra} extra[/]"
        )


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
                -- Solved layers only: those with rankings.
                JOIN map_bounds.map_layer ml ON EXISTS (
                    SELECT 1 FROM map_bounds.map_priority mp WHERE mp.map_layer = ml.id
                )
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
    one_at_a_time: bool = Option(
        False,
        "--one-at-a-time",
        help="Node and commit each piece separately, reporting its time",
    ),
    piece_timeout: float = Option(
        None,
        "--piece-timeout",
        help="Seconds before a piece is abandoned and recorded as failed;"
        " implies --one-at-a-time",
    ),
    reset: bool = Option(
        False,
        "--reset",
        help="First drop the topology and recreate it empty, keeping every map's"
        " bounds, then grid it and re-node every map",
    ),
    grid: bool = Option(
        True,
        "--grid/--no-grid",
        help="Grid an empty topology before noding maps into it",
    ),
    yes: bool = Option(
        False, "--yes", "-y", help="Skip the confirmation prompt where one is allowed"
    ),
):
    """The one command after any edit to maps, bounds or compilations: node the
    maps whose bounds changed, recompile compilation bounds and priority paths,
    re-solve the faces whose owner changed, and rebuild member faces. `--bulk`
    re-nodes the selected maps from scratch.

    An empty topology is gridded first, so no map splits the ocean face whole.
    `--reset` empties it, for a topology whose face labels went wrong; it runs
    unattended once past the write gate."""
    from .reset import reset_topology, topology_is_empty

    if reset:
        if maps:
            raise ValueError("--reset rebuilds the whole topology; it takes no maps")
        require_write_access(WriteScope.Schema, assume_yes=yes, action="topology reset")
    mgr = get_topo_manager()
    db = mgr.database
    if reset:
        t0 = time.time()
        print("Resetting the topology")
        reset_topology(db)
        print(f"[green]Topology recreated empty[/] in {_duration(time.time() - t0)}")
    if grid and topology_is_empty(db):
        print("Empty topology: gridding it before noding maps")
        t0 = time.time()
        seeded = seed_grid(db)
        noded, failed = node_grid(db)
        print(
            f"[green]{seeded}[/] grid lines seeded, [green]{noded}[/] noded,"
            f" [red]{failed}[/] failed in {_duration(time.time() - t0)}"
        )
    mgr.update_full(
        maps,
        bulk=bulk,
        verbose=verbose,
        one_at_a_time=one_at_a_time,
        piece_timeout=piece_timeout,
    )


@cli.command("check")
def check(
    faces: list[int] = Option(
        None, "--face", help="Also report this face; repeat for several"
    ),
    box: str = Option(
        None, help="Also validate this lon/lat box, as xmin,ymin,xmax,ymax"
    ),
    validate: bool = Option(
        False,
        "--validate",
        help=f"Run ValidateTopology on each reported face no wider than"
        f" {MAX_VALIDATE_SPAN:g}°",
    ),
    limit: int = Option(20, help="Report at most this many faces"),
):
    """Find where the topology's face labels disagree with its geometry.

    Collects the faces named in "Side-location conflict" errors from grid lines
    and map pieces, and reports where each is, how many of its edges are the
    grid's, and which maps own the rest -- the maps to re-node if the damage is
    theirs. Read-only.
    """
    from rich.table import Table

    from .check import RING_ERROR, padded, suspect_faces, validate_box, walk_ring

    db = get_database()
    suspects = suspect_faces(db, faces)
    if not suspects:
        print("[green]No face is named in a side-location conflict.[/]")
    gone = [s.face_id for s in suspects if not s.present]
    present = [s for s in suspects if s.present][:limit]

    if present:
        table = Table(title=f"{len(suspects)} faces named in conflicts")
        for col in ("Face", "Mentions", "From", "Box", "Edges", "Grid", "Maps"):
            justify = "left"
            if col in ("Mentions", "Edges", "Grid"):
                justify = "right"
            table.add_column(col, justify=justify)
        for s in present:
            where = "-"
            if s.box is not None:
                where = ", ".join(f"{v:.2f}" for v in s.box)
            maps = ", ".join(s.maps[:4])
            if len(s.maps) > 4:
                maps += f" [dim]+{len(s.maps) - 4}[/]"
            table.add_row(
                str(s.face_id),
                str(s.mentions),
                ", ".join(s.sources),
                where,
                str(s.edges),
                str(s.grid_edges),
                maps or "[dim]none[/]",
            )
        print(table)
    if gone:
        print(
            f"[dim]No longer present (merged or removed): {', '.join(map(str, gone))}[/]"
        )

    tally: dict[str, int] = {}
    for s in present:
        for slug in s.maps or []:
            tally[slug] = tally.get(slug, 0) + 1
    if tally:
        ranked = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
        listed = ", ".join(f"{slug} ({n})" for slug, n in ranked[:10])
        print(f"Maps bounding the most of these faces: {listed}")

    boxes = []
    if validate:
        for s in present:
            if s.span is not None and s.span <= MAX_VALIDATE_SPAN:
                boxes.append((f"face {s.face_id}", padded(s.box)))
            elif s.span is not None:
                print(f"[dim]face {s.face_id} spans {s.span:.0f}°; not validated[/]")
    if box is not None:
        values = tuple(float(v) for v in box.split(","))
        if len(values) != 4:
            raise ValueError("--box takes four numbers: xmin,ymin,xmax,ymax")
        boxes.append(("box", values))
    for label, b in boxes:
        rows = validate_box(db, b)
        if not rows:
            print(f"[green]{label}: valid[/]")
            continue
        print(f"[red]{label}:[/]")
        counts: dict[tuple[str, str | None], int] = {}
        for r in rows:
            counts[(r.error, r.owner)] = counts.get((r.error, r.owner), 0) + 1
        for (error, owner), n in sorted(counts.items(), key=lambda kv: -kv[1]):
            suffix = ""
            if owner:
                suffix = f" [dim]({owner})[/]"
            print(f"  {n} x {error}{suffix}")
        rings = list(dict.fromkeys(r.id1 for r in rows if r.error == RING_ERROR))
        for edge in rings[:RINGS_PER_BOX]:
            _print_ring(walk_ring(db, edge))
        if len(rings) > RINGS_PER_BOX:
            print(f"  [dim]{len(rings) - RINGS_PER_BOX} more rings not walked[/]")


#: Mislabelled rings walked per validated box; each walk is a ring's length.
RINGS_PER_BOX = 5


def _print_ring(ring):
    if ring.error is not None:
        print(f"    [red]ring from edge {ring.edge}: walk failed:[/] {ring.error}")
        return
    labels = []
    for face, n, present in ring.labels:
        gone = ""
        if not present:
            gone = " [red](gone)[/]"
        labels.append(f"{face} x{n}{gone}")
    print(
        f"    ring from edge {ring.edge}: {ring.length} edges label {', '.join(labels)}"
    )
    for edge, face, owner in ring.odd:
        print(f"      [yellow]edge {edge}[/] labels {face} [dim]({owner})[/]")


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
