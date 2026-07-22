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


def create_topo_fixtures(db: Database):
    ctx = create_topo_context(db)
    mgr = MacrostratTopologyManager(ctx)
    mgr.create_tables()


TopologySchema = SchemaDefinition(
    "map-topology",
    provides=[create_topo_fixtures],
    depends_on=["core"],
    environments=frozenset({"local", "development"}),
)


def get_topo_manager():
    db = get_database()
    return MacrostratTopologyManager(create_topo_context(db))


def get_topo_context():
    return get_topo_manager().context
