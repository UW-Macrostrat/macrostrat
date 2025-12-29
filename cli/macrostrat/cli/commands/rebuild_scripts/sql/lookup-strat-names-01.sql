set SEARCH_PATH to macrostrat, public;

DROP TABLE IF EXISTS macrostrat.lookup_strat_names_new;
DROP TABLE IF EXISTS macrostrat.lookup_strat_names_old;

-- Create new empty table mimicking structure of existing lookup_strat_names table
-- Do not carry over not-null constraints etc.
CREATE TABLE macrostrat.lookup_strat_names_new
AS SELECT *
FROM macrostrat.lookup_strat_names
WHERE false;

