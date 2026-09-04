
UPDATE macrostrat.cols_new AS c
SET poly_geom = a.col_area
FROM macrostrat.col_areas a
WHERE c.id = a.col_id;

UPDATE macrostrat.cols_new SET coordinate = ST_GeomFromText(wkt);
UPDATE macrostrat.cols_new SET poly_geom = ST_SetSRID(poly_geom, 4326);

