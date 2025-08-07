/*
Select id of polygon that contains point
*/

SELECT
    id
FROM {topo_schema}.map_face mtm
WHERE ST_Contains(
    mtm.geometry,
    ST_GeomFromGeoJSON(:point)
    );
