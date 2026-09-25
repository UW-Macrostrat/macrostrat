import time
from contextlib import contextmanager
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from mapboard.topology_manager import TopologyManager
from rich import print
from rich.progress import Progress

__dir__ = Path(__file__).parent

proc = lambda name: __dir__ / "procedures" / f"{name}.sql"

#: Snapping tolerance for the first pass over a map's pieces, and the reduced
#: tolerance failed pieces are retried at. The default over-snaps some incoming
#: geometry into failures (curve-not-simple, crosses-edge); a slightly smaller
#: tolerance recovers about a third of them, where exact/0 and densification do
#: not. Both are host decisions: the library nodes what it is given.
NODING_TOLERANCE = 0.0001
RETRY_TOLERANCE = 0.00001

#: Pieces per statement. Each piece is its own call inside the statement, with
#: its own error handling, so this bounds a statement's duration, not its blast
#: radius.
PIECE_BATCH = 100


@contextmanager
def _timed(label: str):
    """Print how long a phase of the update took, so a slow run says where."""
    t0 = time.time()
    yield
    print(f"[dim]{label}: {time.time() - t0:.1f} s[/dim]")


class MacrostratTopologyManager(TopologyManager):
    def remove_maps(self, maps: list[str] = None):
        db = self.database
        all_maps = get_map_list(db, filter_by=maps)
        for _map in all_maps:
            _print_map_info(_map, prefix="Removing map ")
            release_map(db, _map.map_id)
        self.clean_topology()

    def update_full(self, maps: list[str] = None, *, bulk: bool = False):
        """The one command after any edit: node what needs it, then rebuild
        everything downstream -- compilation bounds, priority paths, the faces
        whose identity changed, and the member faces built from them."""
        db = self.database
        update_maps(self, maps, bulk=bulk)

        res = db.run_query(
            """
            SELECT
              count(*) FILTER (WHERE NOT sync.is_current) AS incomplete,
              count(*) FILTER (WHERE sync.failed_pieces > 0) AS with_failures
            FROM map_bounds.map_area a
            JOIN map_bounds.map_area_sync sync ON sync.source_id = a.source_id
            WHERE a.topo IS NOT NULL OR EXISTS (
              SELECT 1 FROM map_bounds.map_topo t WHERE t.source_id = a.source_id
            )
            """
        ).first()
        if res.incomplete:
            print(f"[red]{res.incomplete} maps are not fully noded[/red]")
        if res.with_failures:
            print(
                f"[yellow]{res.with_failures} maps have failed pieces[/yellow]"
                " -- `macrostrat topo errors` lists them"
            )

        # Boundary edits mark faces dirty on their own; identity can change with
        # no boundary moving (a membership or priority edit, a materialization),
        # so ask the resolver which faces it would no longer produce.
        with _timed("Mark stale identity"):
            db.run_sql(proc("mark-stale-identity"))
            db.session.commit()

        # Composite layers are solved by the ordinary face pipeline now that the
        # flattened priority paths give them identity resolution, so the
        # painter's-algorithm overlay is no longer asked for. It stays in the
        # submodule for linework mode. Boundaries are noded above, piece by
        # piece, so the library's whole-row pass is not run.
        with _timed("Dissolve dirty faces"):
            self.update(incremental=True, boundaries=False)

        # Member faces are unions of the solved faces, so they come last.
        with _timed("Sync member faces"):
            db.run_sql(proc("sync-unit-faces"))
            db.session.commit()

        counts = db.run_query(
            """
            SELECT count(*) AS resolved, count(DISTINCT map_layer) AS layers
            FROM map_bounds.map_priority
            """
        ).first()
        print(
            f"[green]{counts.resolved}[/] resolutions across "
            f"[green]{counts.layers}[/] registered compilations"
        )


def release_map(db, map_id: int):
    """Take a map out of the topology: drop its pieces and empty its topogeometry.

    Setting `topo` to NULL fires the library's boundary trigger, which releases
    the topogeometry's primitives and marks the faces it covered dirty.
    `geometry_hash` is cleared so the next update nodes it again from scratch.
    """
    db.run_query(
        "DELETE FROM map_bounds.map_topo WHERE source_id = :map_id",
        dict(map_id=map_id),
    )
    db.run_query(
        """
        UPDATE map_bounds.map_area
        SET topo = NULL, geometry_hash = NULL, topology_error = NULL
        WHERE source_id = :map_id
        """,
        dict(map_id=map_id),
    )
    db.session.commit()


def _print_map_info(map, prefix=""):
    print(
        f"{prefix}[bold green]{map.slug}[/][dim] - #[bold gray]{map.map_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
    )


def get_map_list(db, filter_by: list[str] = None):
    all_maps = db.run_query(
        """
        SELECT
            a.source_id AS map_id,
            slug,
            scale,
            area_km
        FROM map_bounds.map_area a
        JOIN maps.sources s
        ON a.source_id = s.source_id
        -- A compilation is not parted out, materialized or not. Its bounds come
        -- from the `compile` opening operation, and identity resolves a
        -- materialized one through its members' topogeometries.
        --
        -- A *mosaic* is the other way round: its bounds are its own, not
        -- assembled from its members, so it is parted out like an ordinary map.
        WHERE NOT map_bounds.has_faces(a.source_id)
        AND NOT (
          map_bounds.is_compilation(a.source_id)
          AND NOT map_bounds.is_mosaic(a.source_id)
        )
        -- Its members have bounds but are never noded on the mosaic's account:
        -- their extent is their bounds. One that also belongs to a topological
        -- compilation is an ordinary map there and comes back in.
        AND NOT (
          map_bounds.is_mosaic_member(a.source_id)
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.compilation_member cm
            WHERE cm.member_id = a.source_id
              AND NOT map_bounds.is_mosaic(cm.compilation_id)
          )
        )
        ORDER BY area_km DESC
        """
    ).all()
    if filter_by is not None:
        all_maps = list(filter_maps(all_maps, filter_by))
    return all_maps


def filter_maps(all_maps, map_ids: list[str]):
    """Select maps by source id or slug.

    A slug containing `*` or `?` is matched as a glob, so a set of maps can be
    named rather than listed -- `ngs-*` for a compilation's 114 members. Quote it
    in a shell, which would otherwise try to expand it against filenames.
    """
    ids, slugs = split_ids_and_slugs(map_ids)
    patterns = [s for s in slugs if "*" in s or "?" in s]
    exact = set(slugs) - set(patterns)
    for m in all_maps:
        if m.map_id in ids or m.slug in exact:
            yield m
        elif m.slug and any(fnmatch(m.slug, p) for p in patterns):
            yield m


def split_ids_and_slugs(map_ids):
    ids = []
    slugs = []
    for m in map_ids:
        try:
            ids.append(int(m))
        except ValueError:
            slugs.append(m)
    return ids, slugs


def update_maps(
    mgr: MacrostratTopologyManager,
    maps: list[str] = None,
    *,
    clean: bool = True,
    bulk: bool = False,
    subdivide_vertices: int = 256,
):
    """Node every selected map that needs it, then refresh what derives from it."""
    from .bounds.compile import compile_bounds

    db = mgr.database
    start_time = time.time()

    # Seed a boundary for any map that lacks one. Existing boundaries -- including
    # any composed from `boundary_op` -- are left untouched.
    with _timed("Seed missing boundaries"):
        db.run_sql(proc("copy-all-maps"))

    all_maps = get_map_list(db, maps)

    n_processed = 0
    with _timed(f"Check {len(all_maps)} maps"):
        for _map in all_maps:
            if process_map(mgr, _map, bulk=bulk, subdivide_vertices=subdivide_vertices):
                n_processed += 1

    # Cleaning is whole-topology work: `RemoveUnusedPrimitives` visits every
    # primitive and the edge healer every node, whatever changed. Only noding
    # leaves anything for either to find, so a run that noded nothing -- a
    # reprioritization, say -- skips both passes.
    clean = clean and n_processed > 0
    if clean:
        with _timed("Clean topology"):
            mgr.clean_topology()

    # The face-based edge-relation cache is refreshed lazily, not per piece.
    with _timed("Rebuild edge relations"):
        db.run_query("SELECT map_bounds_topology.rebuild_dirty_edge_relations()")
        db.session.commit()

    # A compilation's bounds are the union of the noded sources below it, so
    # they follow the noding.
    with _timed("Compile compilation bounds"):
        for res in compile_bounds(db):
            if res.error:
                print(f"  [red]{res.slug}[/]: {res.error}")
            elif res.built:
                print(f"  [green]{res.slug}[/] -- {res.area_km:,.0f} km²")

    # Flatten the membership tree into the priority paths identity resolution
    # orders by. After bounds: `map_priority` carries only sources with content.
    with _timed("Sync priority paths"):
        db.run_sql(proc("sync-priority-paths"))

    if clean:
        with _timed("Clean topology"):
            mgr.clean_topology()

    print(f"Total time: {time.time() - start_time:.3f} seconds")


def get_maps_with_changed_geometries(mgr: MacrostratTopologyManager):
    """Maps whose topogeometry does not reflect their current bounds."""
    return mgr.db.run_query(
        """
        SELECT
            ma.source_id AS map_id,
            slug,
            area_km
        FROM map_bounds.map_area ma
        JOIN maps.sources s
          ON ma.source_id = s.source_id
        JOIN map_bounds.map_area_sync sync
          ON sync.source_id = ma.source_id
        WHERE ma.geometry IS NOT NULL
          AND NOT sync.is_current
          AND NOT map_bounds.has_faces(ma.source_id)
          AND NOT (
            map_bounds.is_compilation(ma.source_id)
            AND NOT map_bounds.is_mosaic(ma.source_id)
          )
        """
    ).all()


@dataclass
class NodingResult:
    noded: int = 0
    failed: int = 0
    recovered: int = 0


def process_map(
    mgr: MacrostratTopologyManager,
    map,
    *,
    bulk: bool = False,
    subdivide_vertices: int = 256,
) -> bool:
    """Node a map's bounds into its topogeometry, piece by piece.

    A map is current when `geometry_hash` matches its bounds (the library's
    stamp, set here once every piece has been attempted) and no piece is
    pending. Otherwise its pieces are cut -- or resumed, if pieces cut from the
    current bounds are already there -- and each pending piece is noded into
    `map_area.topo` with the library's accumulating call. Failed pieces are
    retried once at a reduced tolerance, then left recorded. `bulk` re-nodes
    from scratch regardless.

    Returns whether anything was noded, so the caller knows if the topology's
    primitives may have changed.
    """
    db = mgr.database
    # The bounds hash is computed once, in a materialized CTE. Written inline in
    # the correlated subquery, Postgres re-hashes the geometry for every piece
    # row it filters: 11,000 pieces of a 22 MB geometry took `global2` past 20
    # minutes before it was hoisted.
    state = db.run_query(
        """
        WITH a AS MATERIALIZED (
          SELECT source_id, md5(ST_AsBinary(geometry))::uuid AS bounds_hash
          FROM map_bounds.map_area
          WHERE source_id = :map_id
        )
        SELECT sync.is_current, sync.pending_pieces, sync.failed_pieces,
               (SELECT count(*) FROM map_bounds.map_topo t
                 WHERE t.source_id = a.source_id
                   AND t.bounds_hash = a.bounds_hash) AS matching_pieces
        FROM a
        JOIN map_bounds.map_area_sync sync ON sync.source_id = a.source_id
        """,
        dict(map_id=map.map_id),
    ).one()

    if state.is_current and not bulk:
        _print_map_info(map, prefix="  Skipping map ")
        print("  Noded from the current bounds")
        return False

    _print_map_info(map, prefix="Processing map ")

    if bulk or state.matching_pieces == 0:
        # Start over: pieces from another geometry (or none), so the
        # topogeometry must hold nothing from before. Emptying it releases its
        # primitives and marks the faces it covered dirty, via the trigger.
        db.run_query(
            """
            UPDATE map_bounds.map_area
            SET topo = NULL, geometry_hash = NULL, topology_error = NULL
            WHERE source_id = :map_id AND (topo IS NOT NULL OR geometry_hash IS NOT NULL)
            """,
            dict(map_id=map.map_id),
        )
        db.session.commit()
        cut_pieces(db, map, subdivide_vertices=subdivide_vertices)
    else:
        print(
            f"  Resuming: {state.pending_pieces} pieces pending,"
            f" {state.failed_pieces} failed"
        )

    result = node_pieces(db, map.map_id)
    print(
        f"  noded {result.noded}, failed {result.failed}"
        + (
            f", recovered {result.recovered} at reduced tolerance"
            if result.recovered
            else ""
        )
    )

    # Every piece has been attempted: the topogeometry is what this geometry
    # gives, failures included. Stamp it complete and record the shortfall.
    db.run_query(
        """
        UPDATE map_bounds.map_area a
        SET geometry_hash = md5(ST_AsBinary(a.geometry))::uuid,
            topology_error = CASE
              WHEN f.n > 0 THEN f.n || ' of ' || f.total || ' pieces failed to node'
              ELSE NULL END
        FROM (
          SELECT count(*) FILTER (WHERE topology_error IS NOT NULL) AS n, count(*) AS total
          FROM map_bounds.map_topo WHERE source_id = :map_id
        ) f
        WHERE a.source_id = :map_id
        """,
        dict(map_id=map.map_id),
    )
    db.session.commit()
    print()
    return True


def cut_pieces(db, _map, *, subdivide_vertices: int = 256) -> int:
    """Cut a map's bounds into the pieces it is noded from (see `cut-pieces.sql`)."""
    simplify_amount = 0.0001
    # Don't simplify the boundaries of fine-scale maps as much.
    if _map.scale == "large":
        simplify_amount = 0.00001

    t_start = time.time()
    n = db.run_query(
        proc("cut-pieces"),
        dict(
            map_id=_map.map_id,
            simplify_amount=simplify_amount,
            subdivide_vertices=subdivide_vertices,
        ),
    ).scalar()
    db.session.commit()
    print(f"  Cut {n} pieces in {time.time() - t_start:.2f} s")
    return n


def _node_batch(db, map_id: int, *, failed: bool, tolerance: float):
    res = db.run_query(
        proc("node-pieces"),
        dict(map_id=map_id, batch_size=PIECE_BATCH, tolerance=tolerance, failed=failed),
    ).one()
    db.session.commit()
    return res.noded or 0, res.failed or 0


def node_pieces(db, map_id: int) -> NodingResult:
    """Node every pending piece of a map, then retry the failures once."""
    result = NodingResult()
    pending = db.run_query(
        """
        SELECT count(*) FROM map_bounds.map_topo
        WHERE source_id = :map_id AND NOT noded AND topology_error IS NULL
        """,
        dict(map_id=map_id),
    ).scalar()
    if pending:
        with Progress() as progress:
            task = progress.add_task("Noding pieces", total=pending)
            while True:
                noded, failed = _node_batch(
                    db, map_id, failed=False, tolerance=NODING_TOLERANCE
                )
                if noded + failed == 0:
                    break
                result.noded += noded
                result.failed += failed
                progress.update(task, advance=noded + failed)

    # One retry at the reduced tolerance, for pieces that just failed and for
    # pieces left failed by an earlier run.
    while True:
        noded, failed = _node_batch(db, map_id, failed=True, tolerance=RETRY_TOLERANCE)
        if noded == 0:
            break
        result.recovered += noded
        result.failed -= noded
    return result
