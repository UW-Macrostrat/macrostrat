-- Append '_polygons' to primary_table names in maps.sources
UPDATE maps.sources SET primary_table = primary_table || '_polygons'
WHERE primary_table NOT LIKE '%_polygons';
