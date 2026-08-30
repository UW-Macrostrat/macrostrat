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

/** The area of full maps in the topology.

  A map''s boundary is described entirely by its `boundary_op` list: an `init`
  operation at position 0 establishes the starting geometry, and later operations
  modify it. `geometry` is the composed result, mirrored to `maps.sources.rgeom`
  for v2 compatibility.

  Because the boundary is a fold rather than a stored edit, re-running `init` and
  replaying the operations preserves every correction instead of freezing it.
*/
CREATE TABLE IF NOT EXISTS map_bounds.map_area (
  /** The key stays `id`: the topology-manager submodule is the boundary table's
    consumer and hard-codes that name -- in `__edge_relation`'s foreign key and in
    a dozen `l.id` / `OLD.id` references across its fixtures and procedures.
    `source_id` is a generated alias, so the column can be read by the name it
    actually holds (a `maps.sources` key) without forking the submodule.
    Note it cannot be *written*: inserts must target `id`. */
  id integer PRIMARY KEY REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  source_id integer GENERATED ALWAYS AS (id) STORED UNIQUE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  geometry_hash uuid,
  topology_error text,
  map_layer integer REFERENCES map_bounds.map_layer(id),
  area_km double precision,
  /** Set when replaying the operation list failed; cleared on a clean compose. */
  boundary_error text
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
  source_id integer REFERENCES map_bounds.map_area(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  -- For tracking whether the geometry and topology are in sync
  geometry_hash uuid,
  topology_error text
);


/** map_topo */
/** The identity column stays `map_id` rather than `source_id`: the
  topology-manager submodule already defines `map_face.source_id` as a
  self-reference (the face a composite face was derived from), so the name is
  taken in this schema and means something else. */
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
-- Every per-map procedure filters on this; without it they seq-scan the table.
CREATE INDEX IF NOT EXISTS map_bounds_map_topo_source_idx ON map_bounds.map_topo (source_id);

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

/** Trigger to force map_area recalculation when a map_topo's topogeometry
  is updated, or a map_topo row is deleted, for a given source_id. */
CREATE OR REPLACE FUNCTION map_bounds.ensure_map_area_recalculation_on_topo_change()
RETURNS trigger
AS $$
DECLARE
  _source_id integer;
BEGIN
  _source_id := NULL;
  IF (TG_OP = 'DELETE' AND OLD.topo IS NOT NULL) THEN
    -- No change to topology if the topo column is null, so we can ignore this change
    _source_id := OLD.source_id;
  ELSEIF (TG_OP = 'UPDATE' AND NOT topology.equals(OLD.topo, NEW.topo)) THEN
    _source_id := NEW.source_id;
  ELSEIF (TG_OP = 'INSERT' AND NEW.topo IS NOT NULL) THEN
    _source_id := NEW.source_id;
  END IF;
  IF (_source_id IS NULL) THEN
    -- No change to topology, so we can ignore this change
    RETURN NULL;
  END IF;
  /** Nothing to mark. `geometry_hash` records which boundary the `map_topo`
    parts were derived from (see `map_area_sync`), so clearing it here would
    force a needless re-subdivision. That a part's topogeometry changed means
    the *assembly* step is stale, which `map_area_sync.assembled` and the
    element-count comparison in `mark-changed-areas` already derive. */
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Add the trigger
CREATE TRIGGER update_map_area_from_topo
AFTER INSERT OR UPDATE OR DELETE ON map_bounds.map_topo
FOR EACH ROW EXECUTE FUNCTION map_bounds.ensure_map_area_recalculation_on_topo_change();

/** Keep `maps.sources.rgeom` in step with the composed boundary.

  `map_area.geometry` is authoritative; `rgeom` is a read-compatibility mirror.
  The v2 API filters on `rgeom IS NOT NULL` and runs point/shape intersection
  against it (`/defs/sources`), and `web_geom` derives from it -- so the column
  must stay populated and GIST-indexed even though nothing writes it directly
  any more.

  A trigger rather than a write in the compose path, so the mirror cannot drift
  regardless of what updates `map_area`. The `IS DISTINCT FROM` guard makes it
  inert when the geometry did not actually change.
*/
CREATE OR REPLACE FUNCTION map_bounds.sync_source_rgeom()
  RETURNS trigger AS $$
BEGIN
  UPDATE maps.sources
  SET rgeom = NEW.geometry
  WHERE source_id = NEW.source_id
    AND rgeom IS DISTINCT FROM NEW.geometry;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER sync_source_rgeom
  AFTER INSERT OR UPDATE OF geometry ON map_bounds.map_area
  FOR EACH ROW EXECUTE FUNCTION map_bounds.sync_source_rgeom();


/** Synchronisation state of each map area, derived rather than flagged.

  The pipeline has four stages, and only the first has an input that cannot be
  recovered from the data: `map_topo` parts are a simplified, subdivided
  transform of `map_area.geometry`, and that transform cannot be inverted. So
  `map_area.geometry_hash` records the boundary those parts were built from --
  exactly what `map_topo.geometry_hash` records one level down, for the geometry
  its topogeometry was built from.

  Everything else is derivable:
    parts_current  the parts still reflect the current boundary
    parts_solved   every part has a topogeometry, or a recorded error
    assembled      map_area.topo has been built from the parts
*/
CREATE OR REPLACE VIEW map_bounds.map_area_sync AS
SELECT
  a.source_id,
  a.geometry_hash IS NOT DISTINCT FROM md5(ST_AsBinary(a.geometry))::uuid
    AS parts_current,
  NOT EXISTS (
    SELECT 1 FROM map_bounds.map_topo t
    WHERE t.source_id = a.source_id
      AND t.topo IS NULL
      AND t.topology_error IS NULL
  ) AS parts_solved,
  a.topo IS NOT NULL AS assembled,
  (
    a.geometry_hash IS NOT DISTINCT FROM md5(ST_AsBinary(a.geometry))::uuid
    AND a.topo IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds.map_topo t
      WHERE t.source_id = a.source_id
        AND t.topo IS NULL
        AND t.topology_error IS NULL
    )
  ) AS is_current
FROM map_bounds.map_area a;


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
  source_id integer REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  priority integer,
  /** Cached bounds for the map's contribution to the compilation. */
  --geometry Geometry(MultiPolygon, 4326),
  PRIMARY KEY (map_layer, source_id)
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
