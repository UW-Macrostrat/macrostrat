/*
Add onto lines route, allows for grabbing one line
*/
SELECT ST_AsGeoJSON(ST_LineMerge(geometry)) lines, id FROM ${data_schema}.linework WHERE id = %(id_)s;