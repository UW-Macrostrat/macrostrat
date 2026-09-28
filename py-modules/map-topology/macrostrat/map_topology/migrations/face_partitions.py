"""Faces belong to served compilations: one partition per (compilation, band)."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, has_columns

#: The compilations only ever solved as part of a served one. The design's list:
#: the carto tree, the `-v1` snapshot's tiers, and the NGS products other than
#: `ngs-bedrock`.
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

_SCALES = ["tiny", "small", "medium", "large"]


_has_band = has_columns("map_bounds", "map_layer", "band")


def _registries_exist(db: Database) -> bool:
    # Each condition is evaluated on its own, before the column exists too.
    if not _has_band(db):
        return False
    return (
        db.run_query(
            """
            SELECT count(DISTINCT band) = 4
            FROM map_bounds.map_layer
            WHERE source_id IS NULL AND band IS NOT NULL
            """
        ).scalar()
        is True
    )


def _carto_bands_exist(db: Database) -> bool:
    if not _has_band(db):
        return False
    return (
        db.run_query(
            """
            SELECT count(*) = 4
            FROM map_bounds.map_layer ml
            JOIN maps.sources s ON s.source_id = ml.source_id
            WHERE s.slug = 'carto' AND ml.band IS NOT NULL
            """
        ).scalar()
        is True
    )


class FacePartitionsMigration(Migration):
    """Key faces by (served compilation, band); scale layers become registries.

    Existing faces are kept where they still answer for something: the carto
    layers' become `carto`'s bands (`carto@small` / `@medium` / `@large`), and
    `tiny`'s becomes `carto@tiny`, with a new `tiny-registry` beside it. The
    `small`, `medium` and `large` rows keep their ids as registries (slugged
    `<scale>-registry`) -- barriers only, never solved -- so every map's
    registration stays where it is; their faces and rankings go. The design's unserved compilations are marked so.

    Sync does the rest on the next `topo update`: it creates the face layers the
    new rule asks for (`carto-v1`'s four bands, `ngs-bedrock`), re-registers the
    few tiny-scale maps, derives the composition, and `mark-stale-identity`
    marks every face of a new layer for the dissolve.
    """

    name = "face-partitions"
    subsystem = "maps"
    description = (
        "Faces keyed by (served compilation, band); scale layers as registries"
    )
    readiness_state = "beta"
    depends_on = ["compilation-multiscale"]
    load_sql_files = False
    # Deletes the scale layers' faces and rankings, and marks sources unserved.
    destructive = True
    sync_chunks = ["map-topology"]

    preconditions = [
        lambda db: not (_registries_exist(db) and _carto_bands_exist(db)),
    ]
    postconditions = [_has_band, _registries_exist, _carto_bands_exist]

    def apply(self, database: Database):
        database.run_sql(
            """
            ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS band maps.map_scale;
            ALTER TABLE map_bounds.map_layer DROP CONSTRAINT IF EXISTS map_layer_source_id_key;
            ALTER TABLE map_bounds.map_layer
              ADD CONSTRAINT map_layer_source_band_key UNIQUE NULLS NOT DISTINCT (source_id, band);
            """,
            raise_errors=True,
        )
        database.run_sql(
            """
            -- The scale compilations carried their names on their layers.
            UPDATE maps.sources s
            SET name = ml.name
            FROM map_bounds.map_layer ml
            WHERE ml.source_id = s.source_id AND s.name IS NULL;

            -- Carto's bands keep the faces already solved for them.
            UPDATE map_bounds.map_layer ml
            SET source_id = map_bounds.source_id('carto'),
                band = CAST(v.band AS maps.map_scale),
                slug = 'carto@' || v.band,
                name = 'Carto (' || v.band || ')',
                topological = true,
                editable = false
            FROM (VALUES
              ('tiny', 'tiny'),
              ('carto-small', 'small'),
              ('carto-medium', 'medium'),
              ('carto-large', 'large')
            ) AS v(slug, band)
            WHERE ml.slug = v.slug;

            -- The other scale layers become registries, keeping their ids -- so
            -- every map's registration stays where it is -- unless a sync has
            -- already seeded the registry, in which case the registrations move
            -- there and the old row goes.
            UPDATE map_bounds.map_area ma
            SET map_layer = r.id
            FROM map_bounds.map_layer old, map_bounds.map_layer r
            WHERE ma.map_layer = old.id
              AND old.slug IN ('small', 'medium', 'large')
              AND r.source_id IS NULL
              AND r.band = CAST(old.slug AS maps.map_scale);
            DELETE FROM map_bounds.map_layer old
            USING map_bounds.map_layer r
            WHERE old.slug IN ('small', 'medium', 'large')
              AND r.source_id IS NULL
              AND r.band = CAST(old.slug AS maps.map_scale);
            UPDATE map_bounds.map_layer
            SET source_id = NULL,
                band = CAST(slug AS maps.map_scale),
                name = name || ' (registry)',
                slug = slug || '-registry'
            WHERE slug IN ('small', 'medium', 'large');

            INSERT INTO map_bounds.map_layer (slug, name, band, min_zoom, max_zoom, bounds, topological)
            VALUES ('tiny-registry', 'Tiny (registry)', 'tiny', 0, 4,
              ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true)
            ON CONFLICT (slug) DO NOTHING;

            -- Registries are never solved.
            DELETE FROM map_bounds_topology.map_face f
            USING map_bounds.map_layer ml
            WHERE f.map_layer = ml.id AND ml.source_id IS NULL;
            DELETE FROM map_bounds_topology.dirty_face d
            USING map_bounds.map_layer ml
            WHERE d.map_layer = ml.id AND ml.source_id IS NULL;
            DELETE FROM map_bounds.map_priority mp
            USING map_bounds.map_layer ml
            WHERE mp.map_layer = ml.id AND ml.source_id IS NULL;
            -- Rebuilt by sync from the maps each face layer solves.
            DELETE FROM map_bounds.map_layer_composition;
            """,
            raise_errors=True,
        )
        database.run_query(
            "UPDATE maps.sources SET is_served = false WHERE slug = ANY(:slugs)",
            dict(slugs=UNSERVED),
        )
        database.session.commit()
