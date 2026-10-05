/** A lon/lat grid of lines noded into the topology, so no face spans the globe.

  A face split costs PostGIS time in proportion to the face's edges, and the
  face outside every map's bounds -- the ocean, held by `global2` -- had 43,000
  of them on development. Grid edges cap any face at one cell's worth.

  Lines, not cells: cells share sides, and a side noded twice fails where
  snapping bent it the first time ("geometry intersects edge", development
  2026-10-04). Each line here belongs to exactly one level -- the coarsest
  spacing that divides its coordinate -- so no two lines are collinear, and a
  line crosses the others and the maps' edges, which PostGIS allows. A line
  runs whole, pole to pole or round the world: a face is split only when an
  edge closes a ring, so a whole line halves every region it crosses as it
  lands, where pieces split nothing until the last one. Lines are noded one
  per transaction, coarse levels first; one that fails at both tolerances is
  noded in cell-side pieces instead (`split_grid_line`).

  The rows are lineal topogeometries: they own their edges, so
  `RemoveUnusedPrimitives` keeps them; they are not rows of the boundary table
  (`map_area`), so `__edge_relation` never lists them and faces with one
  identity join across them. Kept apart from the library's `update_contacts`
  because the library serves one boundary table and `map_area.id` is a
  `maps.sources` key; the investigation note records the trade. */
CREATE TABLE IF NOT EXISTS map_bounds.grid_line (
  id serial PRIMARY KEY,
  geometry Geometry(LineString, 4326) NOT NULL,
  level smallint NOT NULL,
  /** Set when noding the segment failed. */
  topology_error text
);

CREATE UNIQUE INDEX IF NOT EXISTS grid_line_geometry_key
  ON map_bounds.grid_line (ST_AsBinary(geometry));

SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds', 'grid_line', 'topo', 'LINE')
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  JOIN topology.layer
  ON topology.topology.id = topology.layer.topology_id
  WHERE topology.name = 'map_bounds_topology'
    AND topology.layer.schema_name = 'map_bounds'
    AND topology.layer.table_name = 'grid_line'
    AND topology.layer.feature_column = 'topo'
);

CREATE OR REPLACE FUNCTION map_bounds.grid_layer_id()
  RETURNS integer AS $$
SELECT layer_id
FROM topology.layer
WHERE schema_name = 'map_bounds'
  AND table_name = 'grid_line'
  AND feature_column = 'topo';
$$ LANGUAGE SQL STABLE;

/** Node one segment, then mark the faces beside its edges dirty in the barrier
  layer. Where the segment splits a map's edge, the new half has no barrier row
  and nothing queues the owner -- a split edge changes no `relation` row -- and
  `refresh_dirty_face_edge_relations` re-derives the owners of every edge around
  a dirty face, which covers it. The marks go in the barrier layer only, not
  through `mark_faces`, which fans out to every solved layer: splitting a
  primitive changes no map face, since PostGIS puts the new face into every
  topogeometry that held the old one. Returns the number of edges. */
CREATE OR REPLACE FUNCTION map_bounds.node_grid_line(_id integer, _tol float8)
RETURNS integer AS $$
DECLARE
  _tg topology.topogeometry;
BEGIN
  UPDATE map_bounds.grid_line g
  SET topo = topology.toTopoGeom(g.geometry, 'map_bounds_topology', map_bounds.grid_layer_id(), _tol),
      topology_error = NULL
  WHERE g.id = _id;
  -- Not `RETURNING g.topo INTO _tg`: with a composite target PL/pgSQL assigns
  -- the value's fields to the variable's fields, one by one.
  _tg := (SELECT topo FROM map_bounds.grid_line WHERE id = _id);

  INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
  SELECT unnest(map_bounds_topology.relevant_faces(_tg)), map_bounds.barrier_layer()
  ON CONFLICT DO NOTHING;

  RETURN (SELECT count(*) FROM topology.GetTopoGeomElements(_tg));
END;
$$ LANGUAGE plpgsql;

/** The cell-side pieces of a line, at its level, for a line that could not be
  noded whole. The line keeps its row and its error; `ON CONFLICT` keeps pieces
  already present. */
CREATE OR REPLACE FUNCTION map_bounds.split_grid_line(_id integer, _size float8)
RETURNS integer AS $$
DECLARE
  _line map_bounds.grid_line;
  _n integer;
BEGIN
  SELECT * INTO _line FROM map_bounds.grid_line WHERE id = _id;
  WITH pieces AS (
    SELECT ST_LineSubstring(
      _line.geometry,
      i / (ST_Length(_line.geometry) / _size),
      least(1, (i + 1) / (ST_Length(_line.geometry) / _size))
    ) AS geometry
    FROM generate_series(0, ceil(ST_Length(_line.geometry) / _size)::integer - 1) i
  ),
  inserted AS (
    INSERT INTO map_bounds.grid_line (geometry, level)
    SELECT geometry, _line.level FROM pieces
    ON CONFLICT DO NOTHING
    RETURNING 1
  )
  SELECT count(*) INTO _n FROM inserted;
  UPDATE map_bounds.grid_line SET topology_error = 'split: ' || coalesce(topology_error, '') WHERE id = _id;
  RETURN _n;
END;
$$ LANGUAGE plpgsql;
