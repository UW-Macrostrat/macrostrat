SELECT
  d.id,
  uid::text,
  d.name,
  type,
  url,
  dt.name type_name,
  dt.organization,
  ST_AsMVTGeom(ST_Transform(geom, 3857), :envelope),
  -- The below is StraboSpot-specific...we'll have to figure out a better way to do this
  (d.data ->> 'id')::bigint AS spot_id
FROM integrations.dataset d
JOIN integrations.dataset_type dt ON d.type = dt.id
WHERE ST_Intersects(geom,ST_Transform(:envelope, 4326))
  AND dt.organization = :organization
  AND dt.name = :type
