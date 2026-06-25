CREATE OR REPLACE FUNCTION map_bounds.fix_antimeridian(geometry)
  RETURNS geometry AS
$$
DECLARE
  geom geometry;
BEGIN
  geom := $1;
  IF ST_XMax(geom) > 180 OR ST_XMin(geom) < -180 THEN
    geom := ST_ReducePrecision(geom, 1e-6);
    geom := ST_Segmentize(ST_MakeValid(geom)::geography, 10000)::geometry;
    -- split on the meridian
    -- shift left by 180 degrees
    geom := ST_ShiftLongitude(geom);
    -- split on the antimeridian
    geom := ST_Split(geom, ST_GeometryFromText('LINESTRING(180 -90, 180 90)', 4326));
    -- rotate back to the original orientation
    geom := ST_WrapX(geom, 180, -360);
    geom := ST_Multi(ST_CollectionExtract(geom, 3));
    geom := ST_MakeValid(geom);
    --geom := geom::geography::geometry;
    geom := ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3));
  END IF;
  geom := ST_Intersection(geom, ST_MakeEnvelope(-180, -90, 180, 90, 4326));
  RETURN geom;
END;
$$ LANGUAGE plpgsql;

WITH base_features AS (
  SELECT
    source_id,
    ST_Transform(
      ST_Multi(
          ST_CoverageSimplify(
            ST_Union(
              ST_CollectionExtract(
                ST_MakeValid(
                  ST_SnapToGrid(ST_Transform({geom_column}, :srid), 0.01)
                ),
                3
              )
            ),
            10000
          ) OVER ()
        ),
      4326
    ) AS geometry
  FROM {primary_table}
  WHERE {where_clause}
  GROUP BY source_id
)
INSERT INTO maps.sources (source_id, rgeom)
SELECT
  source_id,
     map_bounds.fix_antimeridian(geometry)
FROM base_features;
