import time
from contextlib import contextmanager
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from mapboard.topology_manager import TopologyManager
from mapboard.topology_manager.commands.clean_topology import (
    remove_empty_topogeometries,
)
from rich import print
from rich.progress import Progress

__dir__ = Path(__file__).parent

proc = lambda name: __dir__ / "procedures" / f"{name}.sql"


@contextmanager
def _timed(label: str):
    """Print how long a phase of the update took, so a slow run says where."""
    t0 = time.time()
    yield
    print(f"[dim]{label}: {time.time() - t0:.1f} s[/dim]")


class MacrostratTopologyManager(TopologyManager):
    def clean_topology(self):
        db = self.ctx.database
        res = db.run_query(proc("clear-extra-topogeometries")).scalar()
        db.session.commit()
        print(f"Removed {res} orphaned [cyan]map_topo[/cyan] topogeometries")
        super().clean_topology()
        db.session.commit()

    def remove_maps(self, maps: list[str] = None):
        db = self.database
        # Get a list of maps ordered from large to small
        all_maps = get_map_list(db, filter_by=maps)
        for _map in all_maps:
            _print_map_info(_map, prefix="Removing map ")
            print("Removing existing map topo elements")
            _remove_map_topo_elements(db, _map.map_id)

        self.clean_topology()

    def update_full(
        self, maps: list[str] = None, *, bulk: bool = False, remove: bool = False
    ):
        """Update topology fixtures"""
        # Invalidating maps whose geometries have changed
        # TODO: make this more incremental
        if bulk:
            self.db.run_query(proc("mark-changed-areas"))
            # Update faces that are not linked to maps
            self.db.run_query(
                """
                UPDATE map_bounds_topology.map_face
                SET map_id = map_bounds_topology.identity_for_area(geometry, map_layer)
                WHERE map_id IS null;
                """
            )

        update_maps(self, maps)

        # Error if there are any maps left un-assembled or carrying an error
        res = self.db.run_query(
            """
            SELECT count(*)
            FROM map_bounds.map_area a
            JOIN map_bounds.map_area_sync sync ON sync.source_id = a.source_id
            WHERE NOT sync.assembled OR a.topology_error IS NOT NULL
            """
        ).scalar()
        if res > 0:
            print(f"[red]Found [bold]{res}[/bold] maps without a topogeometry[/red]")

        self.clean_topology()

        # Composite layers are solved by the ordinary face pipeline now that the
        # flattened priority paths give them identity resolution, so the
        # painter's-algorithm overlay is no longer asked for. It stays in the
        # submodule for linework mode, whose `search` strategy has no meaningful
        # `faces_are_joinable` and therefore cannot dissolve a composite.
        self.update(incremental=True, boundaries=False)


def _remove_map_topo_elements(db, map_id: int):
    res = list(
        db.run_query(
            """
            DELETE FROM map_bounds.map_topo
            WHERE source_id = :map_id
            RETURNING id
            """,
            dict(map_id=map_id),
        )
    )
    db.session.commit()
    print(f"Removed {len(res)} map_topo elements")


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
        -- A compilation assembled from members is not parted out, materialized
        -- or not. Its boundary is the union of its members' and already exists in
        -- the topology as their edges; `map_topo` parts are a *simplified*
        -- transform of the boundary, so re-noding one fails where the simplified
        -- line crosses an edge it should have followed.
        -- `sync-compilation-bounds` assembles it by reference instead.
        --
        -- A *mosaic* is the other way round: its boundary is its own, not
        -- assembled from its members, so it is parted out like an ordinary map
        -- when placed. Excluding it would strand the parts it already has.
        WHERE NOT (
          EXISTS (
            SELECT 1 FROM map_bounds.compilation_member cm
            WHERE cm.compilation_id = a.source_id
          )
          AND NOT map_bounds.is_mosaic(a.source_id)
        )
        -- Its members have footprints but are never noded on the mosaic's
        -- account: their extent is their footprint. One that is also placed in
        -- a topological compilation is an ordinary map there and comes back in.
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
    **kwargs,
):
    db = mgr.database
    start_time = time.time()

    # Seed a boundary for any map that lacks one. Existing boundaries -- including
    # any composed from `boundary_op` -- are left untouched.
    with _timed("Seed missing boundaries"):
        db.run_sql(proc("copy-all-maps"))

    # Get a list of maps ordered from large to small
    all_maps = get_map_list(db, maps)

    n_processed = 0
    with _timed(f"Check {len(all_maps)} maps"):
        for _map in all_maps:
            if process_map(db, _map, **kwargs):
                n_processed += 1

    # Cleaning is whole-topology work: `RemoveUnusedPrimitives` visits every
    # primitive and the edge healer every node, whatever changed. Only noding or
    # re-deriving a map's parts leaves anything for either to find, so a run that
    # touched no map's parts -- a reprioritization, say -- skips both passes.
    clean = clean and n_processed > 0
    if clean:
        with _timed("Clean topology"):
            mgr.clean_topology()

    with _timed("Assemble map_area topogeometries"):
        update_map_area_topogeometries(db)

    # A compilation's boundary is the union of its members' face sets, so it can
    # only be assembled once those members have topogeometries.
    with _timed("Sync compilation bounds"):
        db.run_sql(proc("sync-compilation-bounds"))

    # Flatten the composition DAG into the priority paths identity resolution
    # orders by. This follows boundary assembly: `map_priority` carries only
    # members that have content, and a compilation has no `map_area` row until it
    # has been assembled out of its members.
    with _timed("Sync priority paths"):
        db.run_sql(proc("sync-priority-paths"))

    if clean:
        with _timed("Clean topology"):
            mgr.clean_topology()

    print(f"Total time: {time.time() - start_time:.3f} seconds")


def get_maps_with_changed_geometries(mgr: MacrostratTopologyManager):
    """Get a list of maps whose geometries have changed since the last update"""
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
        """
    ).all()


def process_map(db, map, **kwargs) -> bool:
    """Process an individual map by creating topogeometries for its features if needed.
    If run in "bulk" mode, processing will be run on all maps regardless of whether topogeometries
    are already present. Otherwise, processing will be run only on maps that have not changed.

    Returns whether the map's parts were touched, so the caller knows if the
    topology's primitives may have changed.
    """
    bulk = kwargs.pop("bulk", False)
    if not bulk:
        # Test whether we should process this map
        res = db.run_query(
            """
            SELECT 1 FROM map_bounds.map_area_sync
            WHERE source_id = :map_id AND is_current
            """,
            dict(map_id=map.map_id),
        ).scalar()
        if res == 1:
            _print_map_info(map, prefix="  Skipping map ")
            print("  Boundary, parts and assembly are all current")
            return False

        # Every part being solved is only a reason to skip if the parts still
        # reflect the current boundary. Otherwise a recomposed boundary looks
        # "fully processed" on the strength of parts derived from the old one --
        # which is precisely how a stale map goes unnoticed.
        parts_current = db.run_query(
            """
            SELECT parts_current FROM map_bounds.map_area_sync
            WHERE source_id = :map_id
            """,
            dict(map_id=map.map_id),
        ).scalar()
        if parts_current:
            query_sql = proc("get-map-topo-status")
            res = db.run_query(query_sql, dict(map_id=map.map_id)).one()
            if res.total > 0 and res.processed == res.total:
                _print_map_info(map, prefix="  Skipping map ")
                print(f"  {res.processed} topogeometries already processed")
                return False

    _print_map_info(map, prefix="Processing map ")

    kwargs["restart"] = bulk
    prepare_map_topo_features(db, map, **kwargs)
    print()
    add_topogeometries(db, map.map_id)
    print()
    print()
    return True


def prepare_map_topo_features(
    db, _map, *, subdivide_vertices: int = 256, restart=False
):
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

    # Force insertion
    if restart:
        db.run_query(
            "DELETE FROM map_bounds.map_topo WHERE source_id = :map_id",
            dict(map_id=map_id),
        )

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


@dataclass
class TopoUpdateResult:
    updated: int
    failed: int
    remaining: int
    errors: list[str] | None


def _do_update(db, map_id: int) -> TopoUpdateResult:
    batch_size = 100
    tolerance = 0.0001

    res = db.run_query(
        proc("update-topology-row"),
        dict(map_id=map_id, batch_size=batch_size, tolerance=tolerance),
    ).one()
    db.session.commit()
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
    retryable = db.run_query(
        """
        SELECT count(*)
        FROM map_bounds.map_topo
        WHERE source_id = :map_id
          AND topo IS NULL
          AND topology_error IS NOT NULL
        """,
        dict(map_id=map_id),
    ).scalar()
    if retryable == 0:
        return 0

    recovered = 0
    with Progress() as progress:
        task = progress.add_task("Retrying errored map_topo features", total=retryable)
        while True:
            res = db.run_query(
                proc("update-topology-fix-errors"),
                dict(map_id=map_id, batch_size=100, tolerance=tolerance),
            ).one()
            db.session.commit()
            if not res.updated:
                break
            recovered += res.updated
            progress.update(task, advance=res.updated)
    return recovered


def add_topogeometries(db, map_id: int) -> TopoUpdateResult:
    n_remaining = db.run_query(
        """
        SELECT count(*)
        FROM map_bounds.map_topo
        WHERE source_id = :map_id
          AND topo IS NULL
          AND topology_error IS NULL
        """,
        dict(map_id=map_id),
    ).scalar()
    updated = 0
    failed = 0
    errors = []
    if n_remaining > 0:
        with Progress() as progress:
            task = progress.add_task(
                "Updating map_topo topogeometries", total=n_remaining
            )
            while n_remaining > 0:
                res = _do_update(db, map_id)
                n_remaining = res.remaining

                updated += res.updated
                failed += res.failed
                progress.update(task, advance=res.updated + res.failed)

                if res.errors is not None and len(res.errors) > 0:
                    errors.extend(res.errors)
                    for err in res.errors:
                        progress.console.print(f"   [dim]- [red]{err}")

    # Re-attempt insertion failures at a snap tolerance just below the global
    # 0.0001 default. The default over-snaps some incoming geometry into
    # insertion failures (curve-not-simple, crosses-edge); a slightly smaller
    # tolerance recovers a meaningful fraction without the spurious snapping a
    # larger tolerance introduces. (Exact/0 and densification don't help here.)
    recovered = _retry_errors(db, map_id, tolerance=0.00001)
    if recovered > 0:
        updated += recovered
        print(f"  Recovered {recovered} errored features at reduced tolerance")

    if updated > 0:
        # The parts changed, so the assembled map_area topogeometry no longer
        # matches them. Clear the *assembly*, not `geometry_hash` -- that now
        # records which boundary the parts were derived from, and clearing it
        # would force a needless re-subdivision on every run.
        db.run_query(
            "UPDATE map_bounds.map_area SET topo = NULL WHERE source_id = :id",
            dict(id=map_id),
        )
        db.session.commit()

    return TopoUpdateResult(updated, failed, 0, errors)


def update_map_area_topogeometries(db):
    """Once we have inserted topogeometries into the map_topo table, we must update the map_area
    topogeometries to match. Here, we get a list of maps whose topology components have changed
    and create a new topogeometry for each."""

    maps_to_update = db.run_query(
        """
        SELECT ma.source_id AS id, slug
        FROM map_bounds.map_area ma
        JOIN maps.sources s
          ON ma.source_id = s.source_id
        JOIN map_bounds.map_area_sync sync
          ON sync.source_id = ma.source_id
        -- Needs assembling, and has parts to assemble from.
        WHERE NOT sync.assembled
          AND EXISTS (
            SELECT 1
            FROM map_bounds.map_topo mt
            WHERE mt.source_id = ma.source_id
              AND mt.topo IS NOT NULL
        )
        """
    ).all()

    print(f"Updating {len(maps_to_update)} map_area topogeometries")

    for res in maps_to_update:
        map_id = res.id
        print(f"#{map_id} - {res.slug}")
        db.run_query(proc("create-source-topogeometry"), dict(map_id=map_id))
        db.session.commit()

    # Edge-relation maintenance for face-based topogeometries is deferred (the
    # trigger only marks dirty), so rebuild the affected relations now that all
    # of this map's features and its map_area topogeometry are in place.
    print("Rebuilding edge relations")
    n = db.run_query(
        "SELECT map_bounds_topology.rebuild_dirty_edge_relations()"
    ).scalar()
