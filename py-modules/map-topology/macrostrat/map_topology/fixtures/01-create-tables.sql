CREATE SCHEMA IF NOT EXISTS map_bounds;

-- Pick a relatively small tolerance to avoid gaps

ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS slug text UNIQUE;
ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS min_zoom integer;
ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS max_zoom integer;
-- Approximate bounds for the layer
ALTER TABLE map_bounds.map_layer ADD COLUMN IF NOT EXISTS bounds Geometry(MultiPolygon, 4326);

SELECT topology.CreateTopology('map_bounds_topology', 4326, 0.0001)
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  WHERE name = 'map_bounds_topology'
);

/** The area of full maps in the topology */
CREATE TABLE IF NOT EXISTS map_bounds.map_area (
  id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  geometry_hash uuid,
  topology_error text,
  map_layer integer REFERENCES map_bounds.map_layer(id),
  area_km double precision
);

/** Create a topogeometry column for the area of full maps. */
SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds','map_area', 'topo','POLYGON')
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  JOIN topology.layer
  ON topology.topology.id = topology.layer.topology_id
  WHERE topology.name = 'map_bounds_topology'
    AND topology.layer.schema_name = 'map_bounds'
    AND topology.layer.table_name = 'map_area'
    AND topology.layer.feature_column = 'topo'
);

/**
  Store polygonal parts of a map area. This exists to allow for more incremental
  maintenance for map faces
*/
CREATE TABLE IF NOT EXISTS map_bounds.map_topo (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  map_id integer REFERENCES map_bounds.map_area(id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  -- For tracking whether the geometry and topology are in sync
  geometry_hash uuid,
  topology_error text
);


/** map_topo */
ALTER TABLE map_bounds_topology.map_face
  ADD COLUMN map_id integer REFERENCES maps.sources(source_id);
ALTER TABLE map_bounds_topology.face_identity
  ADD COLUMN map_id integer REFERENCES maps.sources(source_id);

SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds','map_topo', 'topo','POLYGON')
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
  JOIN topology.layer
  ON topology.topology.id = topology.layer.topology_id
  WHERE topology.name = 'map_bounds_topology'
    AND topology.layer.schema_name = 'map_bounds'
    AND topology.layer.table_name = 'map_topo'
    AND topology.layer.feature_column = 'topo'
);

CREATE INDEX IF NOT EXISTS map_bounds_map_topo_geometry_idx ON map_bounds.map_topo USING gist (geometry);

/** Function to update topogeometry for a row, updating the geometry hash and setting/clearing
  topology errors as appropriate.
 */
-- Drop the previous signature (which had an unused `densify` parameter) so the
-- replacement below doesn't leave an ambiguous overload behind.
DROP FUNCTION IF EXISTS map_bounds.update_topogeom(map_bounds.map_topo, double precision, integer);

CREATE OR REPLACE FUNCTION map_bounds.update_topogeom(
  map_topo map_bounds.map_topo,
  tolerance double precision DEFAULT 0.0001
) RETURNS text AS
$$
  DECLARE
    _layer_id integer;
    _hash uuid;
    _err_text text;
  BEGIN
    _hash := md5(ST_AsBinary(map_topo.geometry))::uuid;

    -- Get the layer identifier to update
    SELECT layer_id INTO _layer_id
    FROM topology.layer
    WHERE schema_name='map_bounds'
      AND table_name='map_topo'
      AND feature_column='topo';

    IF (_hash = map_topo.geometry_hash) THEN
      -- We already have a valid topogeometry representation
      RETURN null;
    END IF;
    -- Set topogeometry
    UPDATE map_bounds.map_topo l
    SET
      topo = topology.toTopoGeom(
        map_topo.geometry,
        'map_bounds_topology',
        _layer_id,
        tolerance
             ),
      geometry_hash = _hash,
      topology_error = null
    WHERE l.id = map_topo.id;
    RETURN NULL;
  EXCEPTION WHEN others THEN
    _err_text := SQLSTATE || ': ' || SQLERRM;
    -- Set the error
    UPDATE map_bounds.map_topo l
    SET
      topology_error = _err_text
    WHERE l.id = map_topo.id;
    RETURN _err_text;
  END;
$$
LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION map_bounds_topology.get_topological_map_layer(_line map_bounds.map_area)
  RETURNS integer AS $$
SELECT ml.id
FROM map_bounds.map_layer ml
WHERE ml.id = $1.map_layer
  AND ml.composited_from IS NULL
  AND ml.topological;
$$ LANGUAGE SQL IMMUTABLE;


/** Scale key for Carto compilations:
      scaleIsIn = {
        "tiny": ["tiny", "small"],
        "small": ["small", "medium"],
        "medium": ["medium", "large"],
        "large": ["large"],
    }
 */

CREATE TABLE IF NOT EXISTS map_bounds.map_priority (
  map_layer integer REFERENCES map_bounds.map_layer(id) ON DELETE CASCADE,
  map_id integer REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  priority integer,
  /** Cached bounds for the map's contribution to the compilation. */
  --geometry Geometry(MultiPolygon, 4326),
  PRIMARY KEY (map_layer, map_id)
);


CREATE OR REPLACE FUNCTION map_bounds.layer_id(_slug text)
  RETURNS integer AS $$
SELECT id FROM map_bounds.map_layer WHERE slug = _slug;
$$ LANGUAGE SQL IMMUTABLE;

/** View to adjust map priority based on scales
  (higher-scale maps are always higher priority)
 */
CREATE OR REPLACE VIEW map_bounds.scale_priority AS
SELECT
  source_id,
  priority base_priority,
  scale,
  CASE
    WHEN scale = 'tiny' THEN priority - 20000
    WHEN scale = 'small' THEN priority - 10000
    WHEN scale = 'medium' THEN priority
    WHEN scale = 'large' THEN priority + 10000
    ELSE priority
    END AS priority
FROM maps.sources_metadata m
WHERE is_finalized
  AND status_code = 'active';

/** Standard map compilations */
INSERT INTO map_bounds.map_layer (slug, name, min_zoom, max_zoom, bounds, topological)
VALUES
  ('tiny', 'Tiny',  0, 4, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true),
  ('small', 'Small', 4, 8, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true),
  ('medium', 'Medium', 8, 12, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true),
  ('large', 'Large', 12, 18, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true)
ON CONFLICT (slug) DO NOTHING;

/** Composite compilations */
INSERT INTO map_bounds.map_layer (slug, name, min_zoom, max_zoom, bounds, topological, editable, composited_from)
VALUES
 ('carto-small', 'Carto small', 4, 8,
  ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true, false,
  ARRAY[map_bounds.layer_id('tiny'), map_bounds.layer_id('small')]),
 ('carto-medium', 'Carto medium', 8, 12,
  ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true, false,
  ARRAY[map_bounds.layer_id('small'), map_bounds.layer_id('medium')]),
 ('carto-large', 'Carto large', 12, 18,
  ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true, false,
  ARRAY[map_bounds.layer_id('medium'), map_bounds.layer_id('large')])
ON CONFLICT (slug) DO NOTHING;
