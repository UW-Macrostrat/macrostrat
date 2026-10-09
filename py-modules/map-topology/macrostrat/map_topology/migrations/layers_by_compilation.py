"""One layer per solved compilation; multiscale compilations draw their members'."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, has_columns

#: The compilations that exist to build others: the carto tree, the `-v1`
#: snapshot's tiers, and the NGS products other than `ngs-bedrock`. Each is still
#: solved; unserved, it is not requested by name, and a face below it is credited
#: to the first served source instead.
UNSERVED = [
    "tiny",
    "small",
    "medium",
    "large",
    "carto-small",
    "carto-medium",
    "carto-large",
    "tiny-v1",
    "small-v1",
    "medium-v1",
    "large-v1",
    "carto-small-v1",
    "carto-medium-v1",
    "carto-large-v1",
    "ngs-surface",
    "ngs-quaternary",
    "ngs-pre-quaternary",
    "ngs-precambrian",
]

_has_display_scale = has_columns("map_bounds", "map_layer", "display_scale")


def _no_display_scale(db: Database) -> bool:
    return not _has_display_scale(db)


def _source_key_admits_one_null(db: Database) -> bool:
    # The barrier layer is the one row without a compilation.
    return (
        db.run_query(
            """
            SELECT coalesce(bool_or(i.indnullsnotdistinct), false)
            FROM pg_constraint c
            JOIN pg_index i ON i.indexrelid = c.conindid
            WHERE c.conrelid = 'map_bounds.map_layer'::regclass
              AND c.conname = 'map_layer_source_id_key'
            """
        ).scalar()
        is True
    )


class LayersByCompilationMigration(Migration):
    """Key `map_layer` by compilation alone.

    A database keyed by (compilation, display scale) has its multiscale
    compilations' layers handed to the member at each scale -- `carto`'s large
    layer becomes `carto-large`'s, faces and all -- and the column dropped. The
    source key then allows a single NULL, the barrier layer's.

    Sync does the rest on the next `topo update`: it seeds the barrier layer,
    records every map's boundary in it, and creates a layer for every solved
    compilation that lacks one.
    """

    name = "layers-by-compilation"
    owner = None  # its own `apply`, written for the connector's privileges
    subsystem = "maps"
    description = "One layer per solved compilation; multiscale draws its members'"
    readiness_state = "ga"
    depends_on = ["compilation-multiscale"]
    load_sql_files = False
    destructive = False
    sync_chunks = ["map-topology"]

    preconditions = [has_columns("map_bounds", "map_layer", "source_id")]
    postconditions = [_no_display_scale, _source_key_admits_one_null]

    def apply(self, database: Database):
        if _has_display_scale(database):
            database.run_sql(
                """
                UPDATE map_bounds.map_layer ml
                SET source_id = map_bounds.serving_source(ml.source_id, sb.min_zoom)
                FROM map_bounds.scale_band sb
                WHERE ml.display_scale = sb.scale;

                UPDATE map_bounds.map_layer ml
                SET name = coalesce(s.name, s.slug)
                FROM maps.sources s
                WHERE s.source_id = ml.source_id AND ml.display_scale IS NOT NULL;

                ALTER TABLE map_bounds.map_layer DROP COLUMN display_scale;
                """,
                raise_errors=True,
            )
        # The chunk re-sync replaces functions in place, which cannot drop one.
        database.run_sql(
            """
            DROP FUNCTION IF EXISTS map_bounds.solved_partitions();
            ALTER TABLE map_bounds.map_layer
              DROP CONSTRAINT IF EXISTS map_layer_source_id_key;
            ALTER TABLE map_bounds.map_layer
              ADD CONSTRAINT map_layer_source_id_key
              UNIQUE NULLS NOT DISTINCT (source_id);
            """,
            raise_errors=True,
        )
        database.run_query(
            "UPDATE maps.sources SET is_served = false WHERE slug = ANY(:slugs)",
            dict(slugs=UNSERVED),
        )
        database.session.commit()
