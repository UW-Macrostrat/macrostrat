
INSERT INTO macrostrat.intervals_new (id, interval_name, interval_color) VALUES (0, 'Unknown', '#737373');

UPDATE macrostrat.intervals_new SET rank = 6 WHERE interval_type = 'age';
UPDATE macrostrat.intervals_new SET rank = 5 WHERE interval_type = 'epoch';
UPDATE macrostrat.intervals_new SET rank = 4 WHERE interval_type = 'period';
UPDATE macrostrat.intervals_new SET rank = 3 WHERE interval_type = 'era';
UPDATE macrostrat.intervals_new SET rank = 2 WHERE interval_type = 'eon';
UPDATE macrostrat.intervals_new SET rank = 1 WHERE interval_type = 'supereon';
UPDATE macrostrat.intervals_new SET rank = 0 WHERE rank IS NULL;

