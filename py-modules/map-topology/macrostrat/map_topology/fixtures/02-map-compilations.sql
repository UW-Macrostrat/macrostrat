/** Scale key for Carto compilations:
      scaleIsIn = {
        "tiny": ["tiny", "small"],
        "small": ["small", "medium"],
        "medium": ["medium", "large"],
        "large": ["large"],
    }
 */

CREATE TABLE IF NOT EXISTS map_bounds.map_compilation (
  map_layer integer REFERENCES map_bounds.map_layer(id) ON DELETE CASCADE,
  source_id integer REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  priority integer,
  /** Cached bounds for the map's contribution to the compilation. */
  --geometry Geometry(MultiPolygon, 4326),
  PRIMARY KEY (map_layer, source_id)
);


/**
  TODO: this essentially takes the role of the map_topoly.map_face layer table
SELECT topology.AddTopoGeometryColumn('map_bounds_topology', 'map_bounds','map_compilation', 'topo','POLYGON')
WHERE NOT EXISTS (
  SELECT 1
  FROM topology.topology
         JOIN topology.layer
              ON topology.topology.id = topology.layer.topology_id
  WHERE topology.name = 'map_bounds_topology'
    AND topology.layer.schema_name = 'map_bounds'
    AND topology.layer.table_name = 'map_compilation'
    AND topology.layer.feature_column = 'topo'
);
 */

--CREATE INDEX IF NOT EXISTS map_bounds_map_compilation_source_id_idx ON map_bounds.map_compilation (source_id);
-- CREATE INDEX IF NOT EXISTS map_bounds_map_compilation_priority_idx ON map_bounds.map_compilation (priority);
CREATE INDEX IF NOT EXISTS map_bounds_map_compilation_geometry_idx ON map_bounds.map_compilation USING gist (geometry);

-- Fill map compliation table for carto layers

INSERT INTO map_bounds.map_layer (slug, name, min_zoom, max_zoom, bounds)
VALUES ('carto-tiny', 'Carto tiny', 0, 4, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))),
        ('carto-small', 'Carto small', 4, 8, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))),
        ('carto-medium', 'Carto medium', 0, 12, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))),
        ('carto-large', 'Carto large', 0, 18, ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)))
ON CONFLICT (slug) DO NOTHING;

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

