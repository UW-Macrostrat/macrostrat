from pathlib import Path

from mapboard.topology_manager.config import IdentityStrategy, create_context

from macrostrat.core import SchemaDefinition, get_database
from macrostrat.database import Database

from .manager import MacrostratTopologyManager

__dir__ = Path(__file__).parent


config = dict(
    data_schema="map_bounds",
    topo_schema="map_bounds_topology",
    srid=4326,
    tolerance=0.0001,
)


IDENTITY_STRATEGY = IdentityStrategy(
    identity_column="map_id",
    install=lambda ctx: ctx.database.run_fixtures(
        __dir__ / "fixtures" / "03-identity-management.sql"
    ),
    # A composite layer is solved by dissolving, not filled by overlay: identity
    # resolves across its composition closure through `map_priority.priority_path`,
    # and `faces_are_joinable` compares those identities. So a change in a member
    # layer must mark the composite's faces dirty.
    solves_composites=True,
    # `resolve_layer_identity` above resolves a whole layer in one query, which
    # the dissolve caches instead of re-resolving each face once per incident edge.
    bulk_identity=True,
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
        # Explicit file list, not the directory: `03-identity-management.sql`
        # must run later, via IDENTITY_STRATEGY.install, once the core topology
        # functions it depends on exist.
        create_data_tables=lambda ctx: db.run_fixtures(
            [
                __dir__ / "fixtures" / "01-create-tables.sql",
                __dir__ / "fixtures" / "02-boundary-ops-tables.sql",
                __dir__ / "fixtures" / "04-compilation-tables.sql",
            ]
        ),
        notify_triggers=False,
        face_update_engine="plpgsql",
        face_update_mode="move",
    )


def create_topo_fixtures(db: Database):
    ctx = create_topo_context(db)
    mgr = MacrostratTopologyManager(ctx)
    mgr.create_tables(check=False)


# Importing the migrations package registers its `Migration` subclasses, which
# are discovered by subclass lookup rather than by scanning a directory.
from . import migrations  # noqa: E402,F401

TopologySchema = SchemaDefinition(
    "map-topology",
    provides=[
        create_topo_fixtures,
        # Listed as a file as well, so `schema sync --data` can sweep the seed
        # rows out of it -- the callable above is opaque to that pass. `sync`
        # pre-filters to data statements, so the surrounding DDL is ignored, and
        # everything here is idempotent either way.
        __dir__ / "fixtures" / "01-create-tables.sql",
        __dir__ / "fixtures" / "02-boundary-ops-tables.sql",
        __dir__ / "fixtures" / "04-compilation-tables.sql",
    ],
    depends_on=["core"],
    environments=frozenset({"local", "development"}),
)


def get_topo_manager():
    db = get_database()
    return MacrostratTopologyManager(create_topo_context(db))


def get_topo_context():
    # `TopologyManager` exposes the context as `ctx`; there is no `.context`.
    return get_topo_manager().ctx
