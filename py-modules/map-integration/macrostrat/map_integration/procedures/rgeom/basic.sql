SELECT set_config('my.buffer_distance', (:buffer_distance)::text, true);
SELECT set_config('my.fill_holes', (:fill_holes)::text, true);
SELECT set_config('my.source_id', (:source_id)::text, true);
SELECT set_config('my.fix_antimeridian', (:fix_antimeridian)::text, true);
SELECT set_config('my.srid', (:srid)::text, true);

DO
$$
DECLARE
  _source_id integer := current_setting('my.source_id', false)::integer;
  _srid integer := current_setting('my.srid', false)::integer;
  buffer_dist  float := current_setting('my.buffer_distance', false)::float;
  fill_interior boolean := current_setting('my.fill_holes', false)::boolean;
  fix_antimeridian boolean := coalesce(current_setting('my.fix_antimeridian', true)::boolean, true);
  geom geometry;
BEGIN

  -- Get the latest RGeom instance
  SELECT rgeom
  FROM maps.sources
  WHERE source_id = _source_id
  INTO geom;

  geom := ST_Transform(geom, _srid);

  /** Remove interior rings **/

  geom := ST_Multi(ST_CollectionExtract(geom, 3));

  IF buffer_dist > 0 THEN
    geom := ST_Buffer(geom, buffer_dist, 'endcap=round join=round');
    geom := ST_Buffer(geom, -buffer_dist, 'endcap=flat join=mitre');
    IF geom IS NULL THEN
      RAISE EXCEPTION 'Buffering failed';
    END IF;
  END IF;
  geom := ST_MakeValid(geom, 'method=structure');

  IF fill_interior THEN
    -- Drop interior rings from every part. ST_ExteriorRing only accepts a single
    -- POLYGON (it returns NULL for a MULTIPOLYGON, which is what we have whenever
    -- no buffer dissolved the parts), so dump to polygons, rebuild each from its
    -- outer ring, and re-union. ST_Union also merges any parts that overlap once
    -- their holes are filled.
    geom := (
      SELECT ST_Multi(ST_Union(ST_MakePolygon(ST_ExteriorRing((d).geom))))
      FROM ST_Dump(geom) AS d
    );
  END IF;

  IF geom IS NULL THEN
    RAISE EXCEPTION 'Failed at filling interior';
  END IF;

  geom := ST_Transform(geom, 4326);

  -- Remove interior rings

  /** Fix antimeridian **/
  IF fix_antimeridian THEN
    geom := ST_MakeValid(geom);
    geom := ST_Segmentize(geom::geography, 10000);
    geom := ST_Split(geom, ST_GeometryFromText('LINESTRING(180 -90, 180 90)', 4326));
    geom := ST_ShiftLongitude(geom);
    geom := ST_Split(geom, ST_GeometryFromText('LINESTRING(180 -90, 180 90)', 4326));
    geom := ST_WrapX(ST_MakeValid(geom), 180, -360);
    geom := ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))::geometry;
  END IF;

  IF geom IS NULL THEN
    RAISE EXCEPTION 'Failed at fixing antimeridian';
  END IF;

  geom := ST_Intersection(ST_MakeValid(geom), ST_MakeEnvelope(-180, -90, 180, 90, 4326));

  /** We set the final geometry in the map_bounds.map_area table **/
  UPDATE map_bounds.map_area
  SET
    geometry = geom,
    area_km = ST_Area(ST_Segmentize(geometry, 90)::geography) / 1e6
  WHERE id = _source_id;

END;
$$ LANGUAGE plpgsql;



