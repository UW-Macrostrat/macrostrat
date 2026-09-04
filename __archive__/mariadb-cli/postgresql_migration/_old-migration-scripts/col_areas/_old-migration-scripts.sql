--This file contains the variances from the data that existed in Mariadb and Postgresql. This was the initial data dump from Mariadb into
--Postgresql. We're keeping these queries around for reference of the future Postgresql db structure.
--Scripts used by schlep process from v1 macrostrat.


--col_areas
--wkt column was created by converting col_area from geometry to text.
SELECT id, col_id, null as col_area, ST_AsText(col_area) AS wkt
FROM col_areas

--cols


--intervals


--lookup_unit_intervals

--measuremeta

--pbdb_collections

--strat_tree

--units