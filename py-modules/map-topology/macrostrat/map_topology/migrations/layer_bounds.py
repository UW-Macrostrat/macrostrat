"""Open and build the registered compilations' bounds."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

from ..bounds.compile import compile_bounds
from ..bounds.layers import layer_bounds, seed_layer_openings


def _operations_declared(db: Database) -> bool:
    return (
        db.run_query(
            """
            SELECT count(*) = 2 FROM map_bounds.boundary_operation
            WHERE id IN ('world', 'compile')
            """
        ).scalar()
        is True
    )


def _layers_registered(db: Database) -> bool:
    return (
        db.run_query(
            "SELECT EXISTS (SELECT 1 FROM map_bounds.map_layer WHERE source_id IS NOT NULL)"
        ).scalar()
        is True
    )


def _all_built(db: Database) -> bool:
    return all(l.complete for l in layer_bounds(db))


class LayerBoundsMigration(Migration):
    """Give each registered compilation its opening operation and build it.

    The global layers (`tiny`, `small`, `carto-*`) open with `world`; the scale
    layers (`medium`, `large`) open with `compile`, the union of the sources
    below them. A fresh database is seeded with the same openings by
    `create_topo_fixtures`; on an existing one the seed is data the schema
    differ does not carry, so it runs here, and the bounds are built in the same
    step so the layers are served with the bounds the design gives them rather
    than whatever the old union pipeline last wrote.

    An opening that already exists is respected -- someone may have changed it
    by hand -- but every layer is rebuilt from its opening, so the migration
    converges on the declared bounds. `compile` for `medium` unions 33 maps and
    takes about half a minute.
    """

    name = "compilation-layer-bounds"
    subsystem = "maps"
    description = "Open and build the registered compilations' bounds"
    readiness_state = "ga"
    destructive = True
    depends_on = ["map-topo-pieces", "map-bounds-source-id"]

    preconditions = [
        _operations_declared,
        _layers_registered,
        lambda db: not _all_built(db),
    ]
    postconditions = [_operations_declared, _layers_registered, _all_built]

    def apply(self, database: Database):
        areas, openings = seed_layer_openings(database)
        database.session.commit()
        print(f"Seeded {areas} boundary rows and {openings} openings")
        layer_ids = [l.source_id for l in layer_bounds(database)]
        for res in compile_bounds(database, force=True, only=layer_ids):
            if res.error:
                print(f"  {res.slug}: {res.error}")
            elif res.built:
                print(f"  {res.slug} -- {res.area_km:,.0f} km²")
