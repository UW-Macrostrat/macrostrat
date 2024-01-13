
CREATE INDEX ON macrostrat.cols_new (project_id);
CREATE INDEX ON macrostrat.cols_new USING GIST (coordinate);
CREATE INDEX ON macrostrat.cols_new USING GIST (poly_geom);
CREATE INDEX ON macrostrat.cols_new (col_group_id);
CREATE INDEX ON macrostrat.cols_new (status_code);

