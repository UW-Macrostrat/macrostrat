-- Update all columns with unknown geometry to have SRID 4326 (WGS 84)
SELECT
  UpdateGeometrySRID(
    f_table_schema::text,
    f_table_name::text,
    f_geometry_column::text,
    4326
  )
FROM geometry_columns
WHERE srid = 0;