
CREATE INDEX ON macrostrat.col_areas_new (col_id);
CREATE INDEX ON macrostrat.col_areas_new USING GIST (col_area);

