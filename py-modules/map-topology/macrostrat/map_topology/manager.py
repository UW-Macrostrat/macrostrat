import time
from dataclasses import dataclass
from pathlib import Path

from mapboard.topology_manager import TopologyManager
from rich import print

__dir__ = Path(__file__).parent

proc = lambda name: __dir__ / "procedures" / f"{name}.sql"


class MacrostratTopologyManager(TopologyManager):
    def clean_topology(self):
        db = self.ctx.database
        res = db.run_query(proc("clear-extra-topogeometries")).scalar()
        db.session.commit()
        print(f"Removed {res} orphaned [cyan]map_topo[/cyan] topogeometries")
        super().clean_topology()

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

        # Error if there are any maps without a topogeometry added or an error
        res = self.db.run_query(
            """
            SELECT count(*)
            FROM map_bounds.map_area a
            WHERE geometry_hash IS NULL
              AND (topo IS NULL OR topology_error IS NOT NULL)
            """
        ).scalar()
        if res > 0:
            print(f"[red]Found [bold]{res}[/bold] maps without a topogeometry[/red]")

        self.update(incremental=True, composite_layers=True, boundaries=False)


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


def _print_map_info(map, prefix=""):
    print(
        f"{prefix}[bold green]{map.slug}[/][dim] - #[bold gray]{map.map_id}[/bold gray] [green]{map.area_km:.1f}[/green] km²"
    )


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


def filter_maps(all_maps, map_ids: list[str]):
    ids, slugs = split_ids_and_slugs(map_ids)
    for m in all_maps:
        if m.map_id in ids or m.slug in slugs:
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
    # Copy all maps into the schema
    db.run_sql(proc("copy-all-maps"))

    # Associate maps with compilations
    db.run_sql(proc("set-map-priority"))

    # Get a list of maps ordered from large to small
    all_maps = get_map_list(db, maps)

    start_time = time.time()
    for _map in all_maps:
        process_map(db, _map, **kwargs)

    if clean:
        mgr.clean_topology()

    update_map_area_topogeometries(db)

    if clean:
        mgr.clean_topology()

    end_time = time.time()

    print(f"Total time: {end_time - start_time:.3f} seconds")


def get_maps_with_changed_geometries(mgr: MacrostratTopologyManager):
    """Get a list of maps whose geometries have changed since the last update"""
    return mgr.db.run_query(
        """
        SELECT
            ma.id map_id,
            slug,
            area_km
        FROM map_bounds.map_area ma
        JOIN maps.sources s
        ON ma.id = s.source_id
        WHERE geometry IS NOT NULL
          AND geometry_hash IS NULL
           OR geometry_hash <> md5(ST_AsBinary(geometry))::uuid
        """
    ).all()


def process_map(db, map, **kwargs):
    """Process an individual map by creating topogeometries for its features if needed.
    If run in "bulk" mode, processing will be run on all maps regardless of whether topogeometries
    are already present. Otherwise, processing will be run only on maps that have not changed.
    """
    bulk = kwargs.pop("bulk", False)
    if not bulk:
        # Test whether we should process this map
        res = db.run_query(
            """
            SELECT 1
            FROM map_bounds.map_area ma
            WHERE geometry_hash IS NOT NULL
              AND geometry_hash = md5(ST_AsBinary(geometry))::uuid -- geometry matches hash
              AND topo IS NOT null
              AND ma.id = :map_id
            """,
            dict(map_id=map.map_id),
        ).scalar()
        if res == 1:
            _print_map_info(map, prefix="  Skipping map ")
            print("  Geometry has not changed since last update")
            return

        # We also want to skip this step if the topogeometries for the map are full added and processed
        query_sql = proc("get-map-topo-status")
        res = db.run_query(query_sql, dict(map_id=map.map_id)).one()
        if res.total > 0 and res.processed == res.total:
            _print_map_info(map, prefix="  Skipping map ")
            print(f"  {res.processed} topogeometries already processed")
            return

    _print_map_info(map, prefix="Processing map ")

    kwargs["restart"] = bulk
    prepare_map_topo_features(db, map, **kwargs)
    print()
    add_topogeometries(db, map.map_id)
    print()
    print()


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
            "DELETE FROM map_bounds.map_topo WHERE map_id = :map_id",
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

    if updated > 0:
        # We invalidate the geometry hash for this map area, so we can know to recreate
        # the topogeometry on the next update.
        db.run_query(
            "UPDATE map_bounds.map_area SET geometry_hash = NULL WHERE id = :id",
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
        SELECT id, slug FROM map_bounds.map_area ma
        JOIN maps.sources s
        ON ma.id = s.source_id
        WHERE (
            geometry_hash is NULL
                OR geometry_hash != md5(ST_AsBinary(geometry))::uuid -- geometry does not match hash
            )
          AND EXISTS (
            SELECT 1
            FROM map_bounds.map_topo mt
            WHERE mt.map_id = ma.id
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
