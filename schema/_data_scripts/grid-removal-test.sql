/* Would dropping the grid leave a valid topology? A test on one 5° cell,
   inside a transaction that is always rolled back.

   Validates the cell, clears every grid line crossing it, removes the
   primitives only the grid held there, and validates again. Errors that remain
   after the grid is gone are in the maps' own edges, which re-adding the grid
   would hit again.

   Run from `Code/macrostrat`, giving two faces from a "Side-location conflict":

     macrostrat --env production db psql --write -v face1=8931 -v face2=13193 \
       -f schema/_data_scripts/grid-removal-test.sql

   The cell is the one holding the centre of where the two faces' bounding boxes
   overlap. On any error psql stops, and the closed connection rolls back. */

\set ON_ERROR_STOP on
\timing on

BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '15min';
SET LOCAL client_min_messages = warning;

CREATE TEMP TABLE _cell ON COMMIT DROP AS
WITH f AS (
  SELECT
    (SELECT mbr FROM map_bounds_topology.face WHERE face_id = :face1) AS a,
    (SELECT mbr FROM map_bounds_topology.face WHERE face_id = :face2) AS b
),
c AS (
  SELECT ST_Centroid(CASE WHEN ST_Intersects(a, b) THEN ST_Intersection(a, b) ELSE a END) AS p
  FROM f
)
SELECT ST_MakeEnvelope(
  floor(ST_X(p) / 5) * 5, floor(ST_Y(p) / 5) * 5,
  floor(ST_X(p) / 5) * 5 + 5, floor(ST_Y(p) / 5) * 5 + 5, 4326
) AS box
FROM c;

\echo '== cell'
SELECT ST_AsText(box) AS cell,
  (SELECT count(*) FROM map_bounds_topology.edge_data e WHERE e.geom && box) AS edges,
  (SELECT count(*) FROM map_bounds_topology.face f WHERE f.mbr && box) AS faces
FROM _cell;

\echo '== validation, grid in place'
CREATE TEMP TABLE _before ON COMMIT DROP AS
SELECT v.* FROM _cell, LATERAL topology.ValidateTopology('map_bounds_topology', _cell.box) v;

/* Which topogeometry layer owns an edge an error names (signed in ring errors): the grid, a map piece
   layer, or nothing lineal. Errors about faces or nodes report as such. */
SELECT b.error,
  CASE WHEN b.error ILIKE '%edge%' OR b.error ILIKE '%ring%'
       THEN coalesce(l.table_name, 'no lineal owner')
       ELSE 'not an edge' END AS edge_owner,
  count(*)
FROM _before b
LEFT JOIN map_bounds_topology.relation r
  ON r.element_type = 2 AND r.element_id = abs(b.id1)
LEFT JOIN topology.layer l
  ON l.layer_id = r.layer_id
 AND l.topology_id = (SELECT id FROM topology.topology WHERE name = 'map_bounds_topology')
GROUP BY 1, 2
ORDER BY 3 DESC;

\echo '== clearing the grid lines crossing the cell'
SELECT count(topology.clearTopoGeom(g.topo)) AS grid_lines_cleared
FROM map_bounds.grid_line g, _cell
WHERE g.topo IS NOT NULL AND ST_Intersects(g.geometry, _cell.box);

\echo '== removing what only the grid held, in the cell'
SELECT topology.RemoveUnusedPrimitives('map_bounds_topology', box) AS primitives_removed
FROM _cell;

SELECT
  (SELECT count(*) FROM map_bounds_topology.edge_data e WHERE e.geom && box) AS edges,
  (SELECT count(*) FROM map_bounds_topology.face f WHERE f.mbr && box) AS faces
FROM _cell;

\echo '== validation, grid removed'
CREATE TEMP TABLE _after ON COMMIT DROP AS
SELECT v.* FROM _cell, LATERAL topology.ValidateTopology('map_bounds_topology', _cell.box) v;

SELECT a.error,
  CASE WHEN a.error ILIKE '%edge%' OR a.error ILIKE '%ring%'
       THEN coalesce(l.table_name, 'no lineal owner')
       ELSE 'not an edge' END AS edge_owner,
  count(*)
FROM _after a
LEFT JOIN map_bounds_topology.relation r
  ON r.element_type = 2 AND r.element_id = abs(a.id1)
LEFT JOIN topology.layer l
  ON l.layer_id = r.layer_id
 AND l.topology_id = (SELECT id FROM topology.topology WHERE name = 'map_bounds_topology')
GROUP BY 1, 2
ORDER BY 3 DESC;

\echo '== rolling back: nothing above is kept'
ROLLBACK;
