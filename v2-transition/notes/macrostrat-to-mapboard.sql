SET search_path TO mapboard,provo_export,public;

SELECT DISTINCT descrip FROM lines;

-- Line certainty
ALTER TABLE provo_export.lines ADD COLUMN certainty integer;

UPDATE lines SET certainty = 10 WHERE descrip = 'well located';
UPDATE lines SET certainty = 7 WHERE descrip LIKE 'approximately located%';
UPDATE lines SET certainty = 5 WHERE descrip LIKE 'very approximately located%';
UPDATE lines SET certainty = 2 WHERE descrip LIKE 'concealed%';

-- magenta: #FF00FF

INSERT INTO mapboard.linework_type (id, name)
SELECT DISTINCT new_type, new_type FROM lines;


UPDATE linework_type SET color = '#000000' WHERE color IS null;
UPDATE linework_type SET color = '#FF00FF' WHERE id LIKE '%cline';
UPDATE linework_type SET color = '#ADD8E6' WHERE id = 'lineament';

INSERT INTO linework_type (id, name, color)
VALUES ('contact', 'Contact', '#888888');


INSERT INTO linework (geometry, type, certainty)
SELECT geom, new_type, certainty FROM lines;

UPDATE linework_type SET topology = 'default';


INSERT INTO polygon_type (id, name, color, topology)
SELECT 'unit-' || l.legend_id::text, p.name, color, 'default' FROM polygons p
JOIN map_legend ml
  ON ml.map_id = p.map_id
JOIN legend l
  ON l.legend_id = ml.legend_id
GROUP BY (p.name, l.legend_id, color, l.best_age_bottom, l.best_age_top)
ORDER BY (l.best_age_bottom+l.best_age_top)/2;

-- Polygon seed function
CREATE OR REPLACE FUNCTION map_topology.build_polygon_seed(polygon geometry)
RETURNS geometry AS
$$
DECLARE
  circle record;
  radius double precision;
BEGIN
  circle := ST_MaximumInscribedCircle(polygon);
  radius := least(greatest(circle.radius/2, 10), 100);
  RETURN ST_Intersection(ST_Buffer(circle.center, radius), ST_Buffer(polygon, -circle.radius/4));
END;
$$
LANGUAGE plpgsql;


TRUNCATE TABLE mapboard.polygon;

-- Insert polygon seeds
INSERT INTO mapboard.polygon (type, geometry, layer)
SELECT
	'unit-' || l.legend_id::text,
	ST_Multi(map_topology.build_polygon_seed(geom)),
	0
FROM polygons p
JOIN map_legend ml
  ON ml.map_id = p.map_id
JOIN legend l
  ON l.legend_id = ml.legend_id;
 
-- Polygon boundaries

INSERT INTO linework (type, geometry, layer)
SELECT 'contact', ST_Multi(ST_Boundary(geom)), 0 FROM polygons;

-- Colors

SELECT * FROM polygon_type WHERE color IS null;



SELECT edge_id, count(*) FROM map_topology.__edge_relation
GROUP BY edge_id;
--AND edge_id IN (SELECT edge_id FROM map_topology.__edge_relation WHERE type != 'contact')


-- TOPOLOGY HEALING
UPDATE mapboard.linework SET source = 'v1';

SET search_path To mapboard,map_topology,public;

-- Clean up the linework
INSERT INTO mapboard.linework (geometry, type, certainty, source)
SELECT ST_Multi(geom), er.type, certainty, 'topo_clean' FROM edge_data e
JOIN __edge_relation er ON e.edge_id = er.edge_id
JOIN linework ON line_id = id;

DELETE FROM mapboard.linework WHERE source = 'v1';

UPDATE mapboard.linework l SET
  type = l1.new_type,
  certainty = l1.certainty
FROM provo_export.lines l1
WHERE ST_CoveredBy(l.geometry, l1.geom);

-- Testing topology notification
NOTIFY topology, 'test';