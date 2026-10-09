"""The topology context: how the global map topology is configured.

Config-free on purpose -- `config.py` wires this into the schema and the CLI,
which need `macrostrat.core`; the task runner and tests need only this.
"""

from pathlib import Path

from mapboard.topology_manager.config import IdentityStrategy, create_context

from macrostrat.database import Database

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
                __dir__ / "fixtures" / "05-grid.sql",
            ]
        ),
        notify_triggers=False,
        face_update_engine="plpgsql",
        face_update_mode="move",
    )
