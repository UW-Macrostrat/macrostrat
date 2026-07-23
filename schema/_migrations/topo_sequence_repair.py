# Migration that checks for missing topogeometry sequences
# in map_bounds_topology and recreates them if needed
from macrostrat.schema_management.migrations import Migration, ApplicationStatus
from psycopg.sql import Identifier, Literal
from macrostrat.database import Database


class TopoSequenceRepair(Migration):
    name = "topo-schema-sequence-repair"

    def apply(self, db: Database):
        topo_name = "map_bounds_topology"
        missing_sequences = get_missing_sequence_names(db, topo_name)
        if not missing_sequences:
            return

        layers = get_topo_layers(db, topo_name)

        for layer in layers:
            seq_name = f"topogeo_s_{layer.layer_id}"
            if seq_name not in missing_sequences:
                continue
            max_val = db.run_query(
                "SELECT MAX(({feature_column}).id) FROM {table}",
                dict(
                    feature_column=Identifier(layer.feature_column),
                    table=Identifier(layer.schema_name, layer.table_name))
            ).scalar()
            if max_val is None:
                max_val = 0
            create_sequence(
                db, seq_name,
                schema=topo_name,
                starts_with=max_val+1
            )


    def should_apply(self, db: Database):
        # Check if the sequences exist
        # Get topolayer IDs for the map_bounds_topology schema
        # to get candidate sequence names

        topo_name = "map_bounds_topology"
        missing_sequences = get_missing_sequence_names(db, topo_name)
        if missing_sequences:
            return ApplicationStatus.CAN_APPLY
        else:
            return ApplicationStatus.APPLIED


def get_topo_layers(db, topo_name):
    topo_id = db.run_query(
        "SELECT id FROM topology.topology WHERE name = :topo_name",
        dict(topo_name=topo_name)
    ).scalar()

    layers = db.run_query(
        """
        SELECT layer_id, schema_name, table_name, feature_column
        FROM topology.layer WHERE topology_id = :topo_id
        """,
        dict(topo_id=topo_id)
    ).all()

    return layers

def get_missing_sequence_names(db, topo_name):
    missing_names = db.run_query(
        """
        WITH expected_sequence_names AS (
            SELECT 'topogeo_s_' || layer_id relname
            FROM topology.layer
            WHERE topology_id = (
                SELECT id FROM topology.topology
                WHERE name = :topo_name
                LIMIT 1
            )
        )
        SELECT relname FROM expected_sequence_names
        EXCEPT
        SELECT relname
        FROM pg_class
        WHERE relkind = 'S'
          AND oid::regclass::text LIKE :topo_name || '.topogeo_s_%';
        """,
        dict(topo_name=topo_name)
    ).scalars()
    return set(missing_names)


def create_sequence(db, name, *, schema = None, starts_with = 1):
    # Create the sequence in the specified schema with the given starting value

    sequence_name = Identifier(schema, name)

    db.run_sql(
        "CREATE SEQUENCE {sequence_name} START WITH {start}",
        dict(
            sequence_name=sequence_name,
            start=Literal(starts_with)
        ),
        raise_errors=True
    )
