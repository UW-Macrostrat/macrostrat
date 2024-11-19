WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS envelope
), features AS (
  SELECT
    d.id,
    uid,
    d.name,
    type,
    url,
    dt.name type_name,
    dt.organization,
    ST_AsMVTGeom(ST_Transform(geom, 3857), tile.envelope)
  FROM integrations.dataset d
  JOIN tile ON true
  JOIN integrations.dataset_type dt ON d.type = dt.id
  WHERE ST_Intersects(geom,ST_Transform(tile.envelope, 4326))
    AND dt.organization = :organization
    AND dt.name = :type
)
SELECT ST_AsMVT(features, 'default') FROM features
