SET SEARCH_PATH to macrostrat;

DROP TABLE IF EXISTS lookup_unit_intervals_new;
DROP TABLE IF EXISTS lookup_unit_intervals_old;

CREATE TABLE lookup_unit_intervals_new (LIKE lookup_unit_intervals);

