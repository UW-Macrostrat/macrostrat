DROP VIEW IF EXISTS macrostrat_api.cols;
DROP VIEW IF EXISTS macrostrat_api.refs;

ALTER TABLE macrostrat.col_areas ALTER COLUMN col_area TYPE geometry(Geometry, 4326) USING ST_SetSRID(col_area, 4326);
ALTER TABLE macrostrat.cols ALTER COLUMN coordinate TYPE geometry(Geometry, 4326) USING ST_SetSRID(coordinate, 4326);
ALTER TABLE macrostrat.cols ALTER COLUMN poly_geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(poly_geom, 4326);
ALTER TABLE macrostrat.measuremeta ALTER COLUMN geometry TYPE geometry(Geometry, 4326) USING ST_SetSRID(geometry, 4326);
ALTER TABLE macrostrat.pbdb_collections ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE macrostrat.places ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);
ALTER TABLE macrostrat.refs ALTER COLUMN rgeom TYPE geometry(Geometry, 4326) USING ST_SetSRID(rgeom, 4326); 
ALTER TABLE macrostrat.strat_name_footprints ALTER COLUMN geom TYPE geometry(Geometry, 4326) USING ST_SetSRID(geom, 4326);