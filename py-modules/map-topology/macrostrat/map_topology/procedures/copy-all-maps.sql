/* Seed a boundary for every active map that does not have one yet.

   The union is computed from the map's own features rather than read from
   `maps.sources.rgeom`. `rgeom` is now a *mirror* of `map_bounds.map_area.geometry`
   (kept in step by the `sync_source_rgeom` trigger), so seeding from it would be
   circular -- and for a map whose boundary has been composed from operations, it
   would feed the composed result back in as if it were raw. This is the same
   computation the `union` opening operation performs.

   Only maps with no `map_area` row are touched: a composed boundary must never
   be reset by a topology refresh. Restricting to those first also keeps the
   union off every map on every run.

   `source_id` is a generated alias and cannot be written; the key is `id`.
*/
WITH missing AS (
  SELECT
    s.source_id,
    -- `maps.sources.scale` is free text; the cast is guarded to real partition
    -- keys, which also drops maps with no usable scale (`layer_id` would have
    -- returned null for them anyway).
    s.scale::maps.map_scale AS scale
  FROM maps.sources s
  WHERE s.is_finalized
    AND s.status_code = 'active'
    AND s.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds.map_area a WHERE a.id = s.source_id
    )
)
INSERT INTO map_bounds.map_area (id, geometry, area_km, map_layer)
SELECT
  m.source_id,
  u.geometry,
  ST_Area(ST_Segmentize(u.geometry, 90)::geography) / 1e6,
  map_bounds.layer_id(m.scale::text)
FROM missing m
CROSS JOIN LATERAL (
  SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(p.geom)), 3)) AS geometry
  FROM maps.polygons p
  -- Matching on scale as well prunes to the one partition holding this map.
  WHERE p.source_id = m.source_id
    AND p.scale = m.scale
) u
WHERE u.geometry IS NOT NULL
ON CONFLICT (id) DO NOTHING;

-- Backfill area for any row that lacks it.
UPDATE map_bounds.map_area
SET area_km = ST_Area(ST_Segmentize(geometry, 90)::geography) / 1e6
WHERE geometry IS NOT NULL AND area_km IS NULL;
