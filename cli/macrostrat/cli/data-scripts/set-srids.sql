/* Find all geometry columns in the database with no SRID and set their SRIDs to 4326 */
SELECT
  UpdateGeometrySRID(
    f_table_schema::text,
    f_table_name::text,
    f_geometry_column::text,
    4326
  )
FROM
  geometry_columns
WHERE
  srid = 0;
