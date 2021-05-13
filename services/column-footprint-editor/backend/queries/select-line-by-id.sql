/*
Add onto lines route, allows for grabbing one line
*/
SELECT ST_AsGeoJSON(ST_LineMerge(geometry)) lines, id FROM map_digitizer.linework WHERE id = %(id_)s;