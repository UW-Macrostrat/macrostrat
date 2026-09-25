import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from mapboard.topology_manager import TopologyManager
from mapboard.topology_manager.commands.update_faces import (
    FaceUpdateStats,
    update_faces,
)
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


@dataclass
class NodingResult:
    noded: int = 0
    failed: int = 0
    recovered: int = 0


@dataclass
class UpdateSummary:
    """What a `topo update` did, printed once at the end of the run."""

    maps_checked: int = 0
    maps_noded: int = 0
    pieces: NodingResult = field(default_factory=NodingResult)
    compilations_built: int = 0
    compilation_errors: int = 0
    marked_stale: int = 0
    faces: FaceUpdateStats | None = None
    units: int = 0
    units_rebuilt: int = 0
    phases: list[tuple[str, float]] = field(default_factory=list)

    @contextmanager
    def timed(self, label: str):
        """Print how long a phase of the update took, so a slow run says where."""
        t0 = time.time()
        yield
        dt = time.time() - t0
        self.phases.append((label, dt))
        print(f"[dim]{label}: {_duration(dt)}[/dim]")

    def print(self):
        f = self.faces
        rows = [
            (
                "Maps",
                f"{self.maps_checked:,} checked, {self.maps_noded:,} noded, "
                f"{self.maps_checked - self.maps_noded:,} current",
            ),
        ]
        if self.maps_noded:
            p = self.pieces
            rows.append(
                (
                    "Pieces",
                    f"{p.noded:,} noded, {p.failed:,} failed, "
                    f"{p.recovered:,} recovered at reduced tolerance",
                )
            )
        rows.append(
            (
                "Compilations",
                f"{self.compilations_built:,} bounds rebuilt, "
                f"{self.compilation_errors:,} errors",
            )
        )
        rows.append(("Stale identity", f"{self.marked_stale:,} faces marked dirty"))
        if f is not None:
            rows.append(
                (
                    "Faces",
                    f"{f.seeds:,} dirty, {f.components:,} components: "
                    f"{f.created:,} created, {f.updated:,} updated, "
                    f"{f.deleted:,} deleted, {f.shed:,} shed "
                    f"({f.reseeded:,} primitives re-seeded)",
                )
            )
        rows.append(("Unit faces", f"{self.units_rebuilt:,} of {self.units:,} rebuilt"))

        total = sum(dt for _, dt in self.phases)
        slowest = sorted(self.phases, key=lambda x: x[1], reverse=True)[:3]
        rows.append(
            (
                "Time",
                f"{_duration(total)} "
                f"[dim]({', '.join(f'{k}: {_duration(v)}' for k, v in slowest)})[/dim]",
            )
        )

        print("\n[bold]Summary[/bold]")
        for label, text in rows:
            print(f"  {label:<16}{text}")


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, seconds = divmod(round(seconds), 60)
    if minutes < 60:
        return f"{minutes} m {seconds:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} m"


class MacrostratTopologyManager(TopologyManager):
    def remove_maps(self, maps: list[str] = None):
        db = self.database
        all_maps = get_map_list(db, filter_by=maps)
        for _map in all_maps:
            _print_map_info(_map, prefix="Removing map ")
            release_map(db, _map.map_id)
        self.clean_topology()

    def update_full(
        self, maps: list[str] = None, *, bulk: bool = False, verbose: bool = False
    ) -> UpdateSummary:
        """The one command after any edit: node what needs it, then rebuild
        everything downstream -- compilation bounds, priority paths, the faces
        whose identity changed, and the member faces built from them."""
        db = self.database
        summary = update_maps(self, maps, bulk=bulk, verbose=verbose)

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
        with summary.timed("Mark stale identity"):
            n_dirty = _count_dirty_faces(db)
            db.run_sql(proc("mark-stale-identity"))
            db.session.commit()
            summary.marked_stale = _count_dirty_faces(db) - n_dirty

        # Composite layers are solved by the ordinary face pipeline now that the
        # flattened priority paths give them identity resolution, so the
        # painter's-algorithm overlay is no longer asked for. It stays in the
        # submodule for linework mode. Boundaries are noded above, piece by
        # piece, so the library's whole-row pass is not run. What follows is the
        # faces half of the library's `update()`, called directly for its stats.
        with summary.timed("Dissolve dirty faces"):
            summary.faces = update_faces(self.ctx, incremental=True)
        with summary.timed("Clean topology"):
            self.clean_topology()

        # Member faces are unions of the solved faces, so they come last. Units
        # whose primitives did not change are kept, not rebuilt.
        with summary.timed("Sync member faces"):
            units = db.run_sql(proc("sync-unit-faces"))[-1].one()
            db.session.commit()
            summary.units = units.units
            summary.units_rebuilt = units.units - units.kept

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
        summary.print()
        return summary


def _count_dirty_faces(db) -> int:
    return db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()


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
    verbose: bool = False,
) -> UpdateSummary:
    """Node every selected map that needs it, then refresh what derives from it.

    Maps already noded from their current bounds are counted, not listed, unless
    `verbose`."""
    from .bounds.compile import compile_bounds

    db = mgr.database
    summary = UpdateSummary()

    # Seed a boundary for any map that lacks one. Existing boundaries -- including
    # any composed from `boundary_op` -- are left untouched.
    with summary.timed("Seed missing boundaries"):
        db.run_sql(proc("copy-all-maps"))

    all_maps = get_map_list(db, maps)
    summary.maps_checked = len(all_maps)

    with summary.timed(f"Check {len(all_maps)} maps"):
        for _map in all_maps:
            result = process_map(
                mgr,
                _map,
                bulk=bulk,
                subdivide_vertices=subdivide_vertices,
                verbose=verbose,
            )
            if result is not None:
                summary.maps_noded += 1
                summary.pieces.noded += result.noded
                summary.pieces.failed += result.failed
                summary.pieces.recovered += result.recovered
        n_current = summary.maps_checked - summary.maps_noded
        if n_current:
            print(
                f"[dim]{n_current} maps already noded from their current bounds[/dim]"
            )
    n_processed = summary.maps_noded

    # Cleaning is whole-topology work: `RemoveUnusedPrimitives` visits every
    # primitive and the edge healer every node, whatever changed. Only noding
    # leaves anything for either to find, so a run that noded nothing -- a
    # reprioritization, say -- skips both passes.
    clean = clean and n_processed > 0
    if clean:
        with summary.timed("Clean topology"):
            mgr.clean_topology()

    # The face-based edge-relation cache is refreshed lazily, not per piece.
    with summary.timed("Rebuild edge relations"):
        db.run_query("SELECT map_bounds_topology.rebuild_dirty_edge_relations()")
        db.session.commit()

    # A compilation's bounds are the union of the noded sources below it, so
    # they follow the noding.
    with summary.timed("Compile compilation bounds"):
        for res in compile_bounds(db):
            if res.error:
                summary.compilation_errors += 1
                print(f"  [red]{res.slug}[/]: {res.error}")
            elif res.built:
                summary.compilations_built += 1
                print(f"  [green]{res.slug}[/] -- {res.area_km:,.0f} km²")

    # Flatten the membership tree into the priority paths identity resolution
    # orders by. After bounds: `map_priority` carries only sources with content.
    with summary.timed("Sync priority paths"):
        db.run_sql(proc("sync-priority-paths"))

    if clean:
        with summary.timed("Clean topology"):
            mgr.clean_topology()

    return summary


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


def process_map(
    mgr: MacrostratTopologyManager,
    map,
    *,
    bulk: bool = False,
    subdivide_vertices: int = 256,
    verbose: bool = False,
) -> NodingResult | None:
    """Node a map's bounds into its topogeometry, piece by piece.

    A map is current when `geometry_hash` matches its bounds (the library's
    stamp, set here once every piece has been attempted) and no piece is
    pending. Otherwise its pieces are cut -- or resumed, if pieces cut from the
    current bounds are already there -- and each pending piece is noded into
    `map_area.topo` with the library's accumulating call. Failed pieces are
    retried once at a reduced tolerance, then left recorded. `bulk` re-nodes
    from scratch regardless.

    Returns what was noded, or None for a map left as it was, so the caller
    knows if the topology's primitives may have changed. A map left as it was is
    only listed when `verbose`.
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
        if verbose:
            _print_map_info(map, prefix="  Skipping map ")
            print("  Noded from the current bounds")
        return None

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
    return result


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
