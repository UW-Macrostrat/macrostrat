-- Update all columns with unknown geometry to have SRID 4326 (WGS 84)
SELECT
  UpdateGeometrySRID(
    f_table_schema :: text,
    f_table_name :: text,
    f_geometry_column :: text,
    4326
  )
FROM
  geometry_columns
WHERE
  srid = 0;

ALTER TABLE
  macrostrat.measuremeta
ADD
  COLUMN geometry geometry(Geometry, 4326);

UPDATE
  macrostrat.measuremeta
SET
  geometry = ST_SetSRID(ST_MakePoint(lng, lat), 4326);