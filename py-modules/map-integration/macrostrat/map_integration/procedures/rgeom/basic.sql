CREATE OR REPLACE FUNCTION map_bounds.update_rgeom_basic(geometry)
  RETURNS geometry AS
$$
DECLARE
  geom         geometry;
  cleaned      geometry[];
  ring_geom    geometry;
  rec          record;
  buffer_dist  float := 300000;
  min_area     float;
BEGIN
  geom := $1;
  min_area := buffer_dist * buffer_dist;


  /** Remove interior rings **/

  geom := ST_Multi(ST_CollectionExtract(geom, 3));

  geom := ST_Buffer(geom, buffer_dist, 'endcap=round join=round');
  geom := ST_Buffer(geom, -buffer_dist, 'endcap=flat join=mitre');
  geom := ST_MakeValid(geom, 'method=structure');
  geom := ST_MakePolygon(ST_ExteriorRing(geom));

  geom := ST_Transform(geom, 4326);

  -- Remove interior rings

  /** Fix antimeridian **/
  geom := ST_MakeValid(geom);
  geom := ST_Segmentize(geom::geography, 10000);
  geom := ST_Split(geom, ST_GeometryFromText('LINESTRING(180 -90, 180 90)', 4326));
  geom := ST_ShiftLongitude(geom);
  geom := ST_Split(geom, ST_GeometryFromText('LINESTRING(180 -90, 180 90)', 4326));
  geom := ST_WrapX(ST_MakeValid(geom), 180, -360);
  geom := ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))::geometry;

  geom := ST_Intersection(ST_MakeValid(geom), ST_MakeEnvelope(-180, -90, 180, 90, 4326));
  RETURN geom;
END;
$$ LANGUAGE plpgsql;


WITH base_features AS (
  SELECT source_id, rgeom geometry FROM maps.sources WHERE source_id = :source_id
)
UPDATE map_bounds.map_area
SET geometry = map_bounds.update_rgeom_basic(f.geometry)
FROM base_features f
WHERE f.source_id = map_area.id
  AND map_area.id = :source_id;
