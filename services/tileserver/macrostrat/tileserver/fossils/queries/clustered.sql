WITH
tile AS (
  SELECT ST_TileEnvelope(:z, :x, :y) AS envelope,
         tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS envelope_4326
),
collections AS (
  SELECT
    collection_no,
    name,
    tile_layers.tile_geom(
      ST_Intersection(geom, envelope_4326),
      envelope
    ) AS geom
  FROM macrostrat.pbdb_collections, tile
  WHERE
    geom IS NOT NULL
    AND ST_Intersects(geom, envelope_4326)
),
mvt_features AS (
  SELECT collection_no,
         ST_SnapToGrid(geom, 256, 256) AS cluster_geom,
         geom
  FROM collections
),
grouped_features AS (
  SELECT
    tile_utils.cluster_expansion_zoom(ST_Collect(geom), :z) AS expansion_zoom,
    count(*) AS n,
    st_centroid(ST_Collect(geom)) AS geom,
    CASE
      WHEN count(*) < 2 THEN string_agg(f.collection_no::text, ',')
      ELSE null
    END AS collection_no
  FROM mvt_features f
  GROUP BY cluster_geom
)
SELECT ST_AsMVT(row) AS mvt
FROM (SELECT * FROM grouped_features) AS row;
