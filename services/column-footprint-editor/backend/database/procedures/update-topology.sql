
/*Update Contacts*/
SELECT
  l.id,
  ${topo_schema}.update_linework_topo(l) err
FROM ${data_schema}.linework l
WHERE ${topo_schema}.line_topology(l.type) IS NOT null
  AND l.topology_error IS NULL
  AND geometry_hash IS NULL
ORDER BY ST_Length(geometry)
LIMIT 10;

INSERT INTO ${topo_schema}.__edge_relation (edge_id, topology, line_id, type)
SELECT
  (topology.GetTopoGeomElements(topo))[1] edge_id,
  t.topology,
  l.id,
  l.type
FROM ${data_schema}.linework l
JOIN ${data_schema}.linework_type t
  ON l.type = t.id
WHERE topo IS NOT null
  AND t.topology IS NOT null
ON CONFLICT (edge_id, topology) DO NOTHING;

/*Update Faces*/
-- SELECT ${topo_schema}.update_map_face();

/*Clean Topology*/  
DELETE FROM ${topo_schema}.relation
WHERE layer_id = ${topo_schema}.__linework_layer_id()
AND topogeo_id NOT IN (
  SELECT (topo).id
  FROM ${data_schema}.linework
  WHERE topo IS NOT null
);

DELETE FROM ${topo_schema}.relation
WHERE layer_id = ${topo_schema}.__map_face_layer_id()
AND topogeo_id NOT IN (
  SELECT (topo).id
  FROM ${topo_schema}.map_face
  WHERE topo IS NOT null
);

/*Get edge to delete*/
WITH A as(
SELECT
  edge_id
FROM ${topo_schema}.edge_data
WHERE edge_id NOT IN (
  SELECT element_id
  FROM ${topo_schema}.relation
  WHERE element_type = 2
)
)
SELECT topology.ST_RemEdgeNewFace( ${topo_schema}, A.edge_id);

/*Clean Topo 2*/
SELECT topology.ST_RemIsoNode( ${topo_schema},node_id)
FROM ${topo_schema}.node
WHERE node_id NOT IN (SELECT node_id FROM ${topo_schema}.node_edge);

/*Heal Edges*/
WITH node_edge AS (
SELECT
  node_id,
  unnest(edges) edge_id
FROM ${topo_schema}.node_edge
WHERE n_edges = 2
  AND edges[1] != edges[2]
),
ec AS (
SELECT
  node_id,
  array_agg(line_id) contacts,
  array_agg(ec.edge_id) edges,
  count(r.topogeo_id) n_geom
FROM node_edge ne
JOIN ${topo_schema}.__edge_relation ec
  ON ne.edge_id = ec.edge_id
JOIN ${topo_schema}.relation r
  ON ne.edge_id = r.element_id
 AND r.element_type = 2
GROUP BY node_id
),
edges AS (
SELECT
  node_id,
  edges[1] edge1,
  edges[2] edge2,
  n_geom
FROM ec
WHERE contacts[1] = contacts[2]
  AND array_length(edges,1) = 2
  AND array_length(contacts,1) = 2
  AND n_geom < 2
)SELECT ST_ModEdgeHeal(${topo_schema}, edge1, edge2) from edges;



