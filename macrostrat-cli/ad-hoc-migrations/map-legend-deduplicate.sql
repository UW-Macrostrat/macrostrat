
CREATE TABLE map_legend_tmp AS
SELECT DISTINCT ON (legend_id, map_id) legend_id, map_id FROM maps.map_legend;

TRUNCATE TABLE maps.map_legend;
INSERT INTO maps.map_legend (legend_id, map_id)
SELECT legend_id, map_id FROM map_legend_tmp;

DROP TABLE map_legend_tmp;

CREATE UNIQUE INDEX map_legend_map_id_unique_idx ON maps.map_legend (map_id);