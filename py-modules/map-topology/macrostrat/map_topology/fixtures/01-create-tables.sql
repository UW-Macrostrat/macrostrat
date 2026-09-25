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

/** The pieces a map's bounds were cut into for noding.

  A map's bounds can run to a million vertices, and noding them whole fails or
  takes minutes, so they are simplified, subdivided into pieces of a few hundred
  vertices, and each piece is noded into the map's *single* topogeometry
  (`map_area.topo`) with the topology library's accumulating form of
  `update_boundary_topo`. Nothing topological lives here: a piece is a record of
  what was cut (`bounds_hash` says from which bounds), whether it noded, at what
  tolerance, and the error if it did not. Succeeded rows stay so an interrupted
  noding resumes and the parting is reproducible; failed rows are what gets
  retried, inspected, or accepted by eye. Regenerated wholesale when the bounds
  change.
*/
CREATE TABLE IF NOT EXISTS map_bounds.map_topo (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id integer REFERENCES map_bounds.map_area(source_id) ON DELETE CASCADE,
  geometry Geometry(MultiPolygon, 4326) NOT NULL,
  /** The bounds these pieces were cut from: `md5(ST_AsBinary(map_area.geometry))`. */
  bounds_hash uuid,
  noded boolean NOT NULL DEFAULT false,
  /** The snapping tolerance the last attempt used. */
  tolerance double precision,
  topology_error text
);

/* Pieces were once topogeometries of their own, duplicating every primitive
   reference the map's topogeometry holds. The `map-topo-pieces` migration drops
   that layer; these keep the declarative definition in step on any database. */
ALTER TABLE map_bounds.map_topo ADD COLUMN IF NOT EXISTS bounds_hash uuid;
ALTER TABLE map_bounds.map_topo ADD COLUMN IF NOT EXISTS noded boolean NOT NULL DEFAULT false;
ALTER TABLE map_bounds.map_topo ADD COLUMN IF NOT EXISTS tolerance double precision;
ALTER TABLE map_bounds.map_topo DROP COLUMN IF EXISTS geometry_hash;
DROP TRIGGER IF EXISTS update_map_area_from_topo ON map_bounds.map_topo;
DROP FUNCTION IF EXISTS map_bounds.ensure_map_area_recalculation_on_topo_change();
DROP FUNCTION IF EXISTS map_bounds.update_topogeom(map_bounds.map_topo, double precision, integer);
DROP FUNCTION IF EXISTS map_bounds.update_topogeom(map_bounds.map_topo, double precision);

/** The identity column stays `map_id` rather than `source_id`: the
  topology-manager submodule already defines `map_face.source_id` as a
  self-reference (the face a composite face was derived from), so the name is
  taken in this schema and means something else. */
ALTER TABLE map_bounds_topology.map_face
  ADD COLUMN map_id integer REFERENCES maps.sources(source_id);
ALTER TABLE map_bounds_topology.face_identity
  ADD COLUMN map_id integer REFERENCES maps.sources(source_id);

CREATE INDEX IF NOT EXISTS map_bounds_map_topo_geometry_idx ON map_bounds.map_topo USING gist (geometry);
-- Every per-map procedure filters on this; without it they seq-scan the table.
CREATE INDEX IF NOT EXISTS map_bounds_map_topo_source_idx ON map_bounds.map_topo (source_id);

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
  -- `rgeom` is the v2 compatibility mirror, which knows nothing about
  -- compilations: it is a maps-only column. A compilation (has members, or is a
  -- registered layer) is skipped, so a global one's world bounds never reach v2.
  IF EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = NEW.source_id
  ) OR EXISTS (
    SELECT 1 FROM map_bounds.map_layer ml WHERE ml.source_id = NEW.source_id
  ) THEN
    RETURN NULL;
  END IF;

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


/** Noding state of each map area, derived rather than flagged.

  `map_area.geometry_hash` is the topology library's stamp: the topogeometry was
  built from this geometry. The host sets it once every piece has been attempted
  (a failed piece is accepted, recorded, and visible below), and the library's
  boundary trigger clears it -- and empties the topogeometry -- when the bounds
  change. Pieces report their own state.

    noded            the topogeometry was built from the current bounds
    pending_pieces   pieces cut but not yet attempted
    failed_pieces    pieces whose noding failed, with an error recorded
    is_current       noded, and nothing pending
*/
DROP VIEW IF EXISTS map_bounds.map_area_sync;
CREATE VIEW map_bounds.map_area_sync AS
SELECT
  a.source_id,
  a.geometry_hash IS NOT DISTINCT FROM md5(ST_AsBinary(a.geometry))::uuid AS noded,
  a.topo IS NOT NULL AS has_topo,
  (SELECT count(*) FROM map_bounds.map_topo t
    WHERE t.source_id = a.source_id AND NOT t.noded AND t.topology_error IS NULL)
    AS pending_pieces,
  (SELECT count(*) FROM map_bounds.map_topo t
    WHERE t.source_id = a.source_id AND t.topology_error IS NOT NULL)
    AS failed_pieces,
  (
    a.geometry_hash IS NOT DISTINCT FROM md5(ST_AsBinary(a.geometry))::uuid
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds.map_topo t
      WHERE t.source_id = a.source_id AND NOT t.noded AND t.topology_error IS NULL
    )
  ) AS is_current
FROM map_bounds.map_area a;


/** The layer a boundary row is noded in, or NULL for a row the library must not
  node whole: the host nodes maps piece by piece (`process_map`) and stamps
  `geometry_hash` itself, and a compilation that is not a mosaic is never noded
  at all -- its bounds are composed, and identity resolves it through its
  members. Only the layer test is the library's; the compilation test keeps the
  whole-row pass (`update_contacts`) away from rows it has no business with. */
CREATE OR REPLACE FUNCTION map_bounds_topology.get_topological_map_layer(_line map_bounds.map_area)
  RETURNS integer AS $$
SELECT ml.id
FROM map_bounds.map_layer ml
WHERE ml.id = $1.map_layer
  AND NOT map_bounds.is_composite_layer(ml.id)
  AND ml.topological
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.map_layer r WHERE r.source_id = $1.source_id
  )
  AND NOT (
    EXISTS (
      SELECT 1 FROM map_bounds.compilation_member cm
      WHERE cm.compilation_id = $1.source_id
    )
    AND NOT EXISTS (
      SELECT 1 FROM map_bounds.compilation c
      WHERE c.source_id = $1.source_id AND c.assembly_mode = 'mosaic'
    )
  );
$$ LANGUAGE SQL STABLE;


/** Derived: one row per registered compilation per resolved map. Rebuilt outright
  by `sync-priority-paths`; the columns are declared in `04-compilation-tables.sql`. */
CREATE TABLE IF NOT EXISTS map_bounds.map_priority (
  map_layer integer REFERENCES map_bounds.map_layer(id) ON DELETE CASCADE,
  map_id integer REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  PRIMARY KEY (map_layer, map_id)
);


/** `identity_for_face` joins `relation` to `map_area` on the topogeometry id, and
  a composite field access cannot use an ordinary index -- so without this every
  call sequentially scanned `map_area`, whose rows are wide. That scan was ~1.4ms,
  invoked twice per candidate edge inside the face dissolve, which is the bulk of
  a topology update. With the index the same lookup is ~18us.

  Only `(topo).id` is indexed: `(topo).layer_id` is constant by construction --
  the `check_topogeom_topo` constraint pins it -- so it adds nothing.
*/
CREATE INDEX IF NOT EXISTS map_area_topogeom_id_idx
  ON map_bounds.map_area (((topo).id));


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
INSERT INTO map_bounds.map_layer (slug, name, min_zoom, max_zoom, bounds, topological, editable)
VALUES
 ('carto-small', 'Carto small', 4, 8,
  ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true, false),
 ('carto-medium', 'Carto medium', 8, 12,
  ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true, false),
 ('carto-large', 'Carto large', 12, 18,
  ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326)), true, false)
ON CONFLICT (slug) DO NOTHING;

/** Carto layer membership. `carto-large` is the compilation of `medium` and
  `large`; higher priority wins where they overlap. These are ordinary
  membership edges -- a served layer is still just a compilation. Seeded in
  `04-compilation-tables.sql`, which is where layer source identities are
  assigned. */
