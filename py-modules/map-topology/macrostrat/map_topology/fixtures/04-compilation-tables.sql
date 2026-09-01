/**
  COMPILATIONS

  A compilation is a map -- a `maps.sources` row assembled from other maps. It is
  not a distinct kind of thing, so there is no `map_type` column anywhere:
  "is a compilation" means *has members*, "is a constituent" means *is a member*,
  and both are read straight off `compilation_member`. Whether a map holds polygons
  of its own separates a materialized compilation from a virtual one, and a
  constituent from a map that simply has not been ingested yet.
*/

CREATE TABLE IF NOT EXISTS map_bounds.compilation_member (
  compilation_id integer NOT NULL
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  member_id integer NOT NULL
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  /** Higher wins where members overlap. NULL for a disjoint mosaic, where
    nothing overlaps and the ordering carries no meaning. */
  priority integer,
  /** Open vocabulary, left for the stage that needs it (Stage E wants an
    `updated_by` value for SGMC's editorial artifacts). NULL is a plain member. */
  role text,
  PRIMARY KEY (compilation_id, member_id),
  CONSTRAINT compilation_member_no_self_reference
    CHECK (compilation_id != member_id)
);

CREATE INDEX IF NOT EXISTS compilation_by_member_idx
  ON map_bounds.compilation_member (member_id);

/** Compilation-level attributes.

  Keyed on the compilation rather than added to `maps.sources`, which is a wide
  shared table that listings already struggle with. A compilation with no row
  here takes the defaults; the row records decisions, not existence.
*/
CREATE TABLE IF NOT EXISTS map_bounds.compilation (
  source_id integer PRIMARY KEY
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  /** `layered`: members overlap and priority resolves them.
      `disjoint`: members mosaic cleanly, so overlap resolution can be skipped.
    Not derivable -- whether members overlap is an assertion the operator makes. */
  assembly_mode text NOT NULL DEFAULT 'layered'
    CHECK (assembly_mode IN ('disjoint', 'layered')),
  /** Where the compilation's polygons came from -- NULL while it has none.

    `derived`: assembled from its members by `materialize`, and reversible by
    `dematerialize`, which is safe precisely because the members still hold the
    originals. Every compilation materialized so far.

    `ingested`: the polygons arrived with the compilation and its members record
    *where they came from*. SGMC is the case -- 312,286 polygons ingested as one
    map, decomposable into the 65 published state maps Macrostrat has never held
    separately. Those members are documentary: real sources with citations, URLs
    and footprints, but no polygons, no linework in the topology, no faces.

    NULL is the virtual case, and the column is co-extensive with
    `holds_polygons` by construction: polygons with no recorded provenance, or a
    provenance with no polygons, is a bug either way.

    Not derivable, and not cosmetic. It decides whether a compilation's boundary
    is its own or gets overwritten from its members, and it is what stops
    `dematerialize` from deleting an ingested dataset it mistook for a cache. */
  content text
    CHECK (content IN ('ingested', 'derived')),
  /** The member set the compilation's derived polygons were built from. NULL
    while virtual; stale once it no longer matches the current members. */
  member_hash uuid,
  /** The member state the *boundary* was last assembled from. Separate from
    `member_hash`: the footprint and the polygon cache are independent derived
    things and go stale for different reasons. */
  assembly_hash uuid,
  note text
);

/** A LAYER IS A SERVED COMPILATION

  `map_layer` is not a second kind of thing. `large` is the compilation of all
  large-scale maps; `carto-large` is the compilation of `medium` and `large`.
  What a `map_layer` row adds is that the compilation is **served as a tile
  layer**, so its dissolve is cached in `map_face` and it carries a zoom range.
  That is a deployment decision, not an ontological one.

  The key stays `id`: the submodule's `map_face`, `face_identity` and
  `dirty_face` all reference it. `source_id` is the bridge into the map world,
  the same trick `map_area` uses for the opposite reason.
*/
ALTER TABLE map_bounds.map_layer
  ADD COLUMN IF NOT EXISTS source_id integer UNIQUE
    REFERENCES maps.sources(source_id) ON DELETE SET NULL;

/** Give every served layer a map identity, so it can hold and be held as a
  compilation member. Layers hold no polygons, so they are never an answer to
  identity resolution -- see `holds_polygons` below. */
INSERT INTO maps.sources (slug, status_code, is_finalized)
SELECT ml.slug, 'active', false
FROM map_bounds.map_layer ml
WHERE ml.slug IS NOT NULL
  AND ml.source_id IS NULL
ON CONFLICT (slug) DO NOTHING;

UPDATE map_bounds.map_layer ml
SET source_id = s.source_id
FROM maps.sources s
WHERE s.slug = ml.slug
  AND ml.source_id IS NULL;

/** Whether a compilation is served as a tile layer -- i.e. has its dissolve
  cached in `map_face`. The only thing that distinguishes a "layer" from any
  other compilation. */
CREATE OR REPLACE FUNCTION map_bounds.is_served_layer(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.map_layer WHERE source_id = _source_id
);
$$ LANGUAGE SQL STABLE;

/** Whether a compilation's polygons were ingested with it rather than assembled
  from its members -- so its members are provenance, not material. See
  `compilation.content`. A map that is not a compilation is trivially not one. */
CREATE OR REPLACE FUNCTION map_bounds.is_ingested(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation c
  WHERE c.source_id = _source_id AND c.content = 'ingested'
);
$$ LANGUAGE SQL STABLE;

/** Whether a map's footprint is recorded for reference only -- a documentary
  member of a compilation whose content was ingested. Such a map is never parted
  out into `map_topo`, never enters the topology, and therefore owns no faces. */
CREATE OR REPLACE FUNCTION map_bounds.is_documentary(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation_member cm
  WHERE cm.member_id = _source_id
    AND map_bounds.is_ingested(cm.compilation_id)
);
$$ LANGUAGE SQL STABLE;

/** Whether a map holds polygons of its own, and is therefore a leaf for identity
  resolution: the flattening descends *virtual* compilations and stops at
  materialized ones, which hold the polygons. `is_finalized` is the cached
  `has_map_schema_data` flag, so this is a lookup rather than a scan of the
  partitioned polygon table. */
CREATE OR REPLACE FUNCTION map_bounds.holds_polygons(_source_id integer)
  RETURNS boolean AS $$
SELECT coalesce(is_finalized, false)
FROM maps.sources
WHERE source_id = _source_id;
$$ LANGUAGE SQL STABLE;

/** A stamp over the member set, for detecting a stale polygon cache. */
CREATE OR REPLACE FUNCTION map_bounds.compilation_member_hash(_source_id integer)
  RETURNS uuid AS $$
SELECT md5(string_agg(
    member_id || '/' || coalesce(priority, 0),
    ',' ORDER BY member_id
  ))::uuid
FROM map_bounds.compilation_member
WHERE compilation_id = _source_id;
$$ LANGUAGE SQL STABLE;

/** Membership is traversed recursively, so a cycle does not merely give a wrong
  answer -- it fails to terminate. */
CREATE OR REPLACE FUNCTION map_bounds.check_compilation_member()
  RETURNS trigger AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE ancestors AS (
      SELECT NEW.compilation_id AS id
      UNION
      SELECT mc.compilation_id
      FROM map_bounds.compilation_member mc
      JOIN ancestors a ON mc.member_id = a.id
    )
    SELECT 1 FROM ancestors WHERE id = NEW.member_id
  ) THEN
    RAISE EXCEPTION USING MESSAGE =
      'Map ' || NEW.compilation_id || ' cannot include ' || NEW.member_id
      || ' - that would create a cycle';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER check_compilation_member_trigger
  BEFORE INSERT OR UPDATE ON map_bounds.compilation_member
  FOR EACH ROW EXECUTE FUNCTION map_bounds.check_compilation_member();

/** FLATTENED RESOLUTION

  `map_priority` is now **entirely derived**. Every authored edge lives in
  `compilation_member`; this table is what `sync-priority-paths` produces from it,
  and it exists so identity resolution can be a single indexed lookup rather than
  a recursive walk.

  `priority_path` is a map's effective standing under a served layer: the priority
  of every edge on the way down, concatenated. Postgres compares arrays
  lexicographically, so resolution keeps its shape and only changes what it orders
  by. Where paths share a prefix the deeper one wins -- a map placed inside a
  compilation is more specifically placed than one sitting directly in the layer.
*/
ALTER TABLE map_bounds.map_priority
  ADD COLUMN IF NOT EXISTS priority_path integer[];
ALTER TABLE map_bounds.map_priority DROP COLUMN IF EXISTS derived;
ALTER TABLE map_bounds.map_priority DROP COLUMN IF EXISTS priority;
/** The direct member of `map_layer` through which this map is reached -- itself,
  when it sits directly in the layer. `priority_path` records the priorities along
  the way but not the nodes, and rendering needs the node: a face in `carto-large`
  belongs to member `medium` from that layer's point of view, even though the map
  that actually owns it is two levels further down. */
ALTER TABLE map_bounds.map_priority
  ADD COLUMN IF NOT EXISTS via integer REFERENCES maps.sources(source_id);

/** Carto composition. `carto-large` is the compilation of `medium` and `large`;
  higher priority wins where they overlap. Ordinary membership edges between
  compilations that happen to be served. */
INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
SELECT parent.source_id, member.source_id, v.priority
FROM (VALUES
  ('carto-small',  'tiny',   1),
  ('carto-small',  'small',  2),
  ('carto-medium', 'small',  1),
  ('carto-medium', 'medium', 2),
  ('carto-large',  'medium', 1),
  ('carto-large',  'large',  2)
) AS v(parent_slug, member_slug, priority)
JOIN map_bounds.map_layer parent ON parent.slug = v.parent_slug
JOIN map_bounds.map_layer member ON member.slug = v.member_slug
WHERE parent.source_id IS NOT NULL
  AND member.source_id IS NOT NULL
ON CONFLICT (compilation_id, member_id) DO NOTHING;

/** THE COMPOSITE TOPOGEOMETRY

  A compilation's boundary is the union of its members', and both are already in
  the topology -- so it should reference them, not re-list every face they cover.
  Representing `tiny` (one member) as 94,693 face elements is absurd; as one
  reference it is one row.

  This is PostGIS's hierarchical topology: a level-1 layer whose `child` is the
  level-0 `map_area.topo` layer. `relationtrigger()` enforces that every element
  comes from the child layer, so a layer holds exactly one level of nesting.
  Rather than add a layer per level, a compilation references its *transitive
  leaf* members -- the maps that actually hold polygons. That works at any depth
  with a single layer, and costs 619 elements across the whole system where the
  face representation cost 621,443.

  Compilations therefore live in this layer and leave `topo` NULL; ordinary maps,
  whose boundaries genuinely node into the topology, keep `topo` and leave this
  NULL.
*/
SELECT topology.AddTopoGeometryColumn(
  'map_bounds_topology',
  'map_bounds',
  'map_area',
  'composite_topo',
  'POLYGON',
  (
    SELECT layer_id FROM topology.layer
    WHERE schema_name = 'map_bounds'
      AND table_name = 'map_area'
      AND feature_column = 'topo'
  )
)
WHERE NOT EXISTS (
  SELECT 1 FROM topology.layer
  WHERE schema_name = 'map_bounds'
    AND table_name = 'map_area'
    AND feature_column = 'composite_topo'
);

/** What each compilation's boundary should be assembled from, and whether it
  already has been.

  `elements` is the `createTopoGeom` argument: one reference per transitive leaf
  member. `current_hash` covers both the member set and each member's
  topogeometry id, so a member's boundary being rebuilt makes its parents stale
  too -- `createTopoGeom` mints a new id every time, so the reference would
  otherwise dangle.

  Resolving a hierarchical topogeometry to a geometry costs tens of seconds, so
  the point of this view is to do it only for compilations that actually moved.
*/
CREATE OR REPLACE VIEW map_bounds.compilation_assembly AS
WITH RECURSIVE descendants AS (
  -- A compilation that owns its content is not assembled from anything: its
  -- members are provenance. Excluding it here is what keeps every consumer of
  -- this view -- boundary read-back, `face_elements`, staleness -- from acting
  -- on a compilation whose boundary is authored rather than derived.
  SELECT cm.compilation_id AS root, cm.member_id
  FROM map_bounds.compilation_member cm
  WHERE NOT map_bounds.is_ingested(cm.compilation_id)
  UNION
  SELECT d.root, cm.member_id
  FROM descendants d
  JOIN map_bounds.compilation_member cm
    ON cm.compilation_id = d.member_id
  -- Stop at a map that holds polygons: it is a leaf, not a container.
  WHERE NOT map_bounds.holds_polygons(d.member_id)
)
SELECT
  d.root AS source_id,
  -- References to the members' own topogeometries, for the hierarchical layer.
  array_agg(DISTINCT ARRAY[(a.topo).id, (a.topo).layer_id]) AS elements,
  -- The primitive faces those members cover. A *materialized* compilation needs a
  -- level-0 topogeometry as well, because `identity_for_face` resolves there and
  -- a compilation cannot own a face without one. Assembled by reference either
  -- way: its boundary is already in the topology as its members' edges, and
  -- re-noding a simplified transform of it fails where the simplified line
  -- crosses an edge it should have followed.
  array_agg(DISTINCT ARRAY[r.element_id, 3]) AS face_elements,
  md5(string_agg(DISTINCT
        d.member_id || '/' || (a.topo).id, ',')
      )::uuid AS current_hash,
  c.assembly_hash,
  c.assembly_hash IS DISTINCT FROM
    md5(string_agg(DISTINCT d.member_id || '/' || (a.topo).id, ','))::uuid
    AS is_stale
FROM descendants d
JOIN map_bounds.map_area a
  ON a.source_id = d.member_id
 AND a.topo IS NOT NULL
JOIN map_bounds_topology.relation r
  ON r.layer_id = (a.topo).layer_id
 AND r.topogeo_id = (a.topo).id
 AND r.element_type = 3
LEFT JOIN map_bounds.compilation c ON c.source_id = d.root
GROUP BY d.root, c.assembly_hash;

/** Every map a compilation resolves to, with the *unit* each is presented as.

  A unit is the first member on the way down that is not a served layer. Layers
  are structural -- `carto-large` is assembled from `medium` and `large`, but
  neither is a thing anyone means to see, and both carry only an envelope. The
  meaningful answer is one level further: British Columbia appears as
  `bc-surface`, not as two layers and not as its two constituent maps.

  `_deep` chooses where the descent stops. By default it stops where the polygons
  are -- a materialized compilation is an answer in its own right, so resolution
  goes no further. Set it to descend all the way to maps with no members of their
  own: the referenceable units of mapping, which stay reachable whether or not
  anything above them has been materialized.

  A map with no compilation above it is its own unit.
*/
CREATE OR REPLACE FUNCTION map_bounds.compilation_leaves(
  _source_id integer,
  _deep boolean DEFAULT false
)
  RETURNS TABLE (source_id integer, via integer) AS $$
WITH RECURSIVE descent AS (
  SELECT
    cm.member_id,
    CASE WHEN map_bounds.is_served_layer(cm.member_id) THEN NULL ELSE cm.member_id END
      AS via
  FROM map_bounds.compilation_member cm
  WHERE cm.compilation_id = _source_id
  UNION ALL
  SELECT
    cm.member_id,
    coalesce(
      d.via,
      CASE WHEN map_bounds.is_served_layer(cm.member_id) THEN NULL ELSE cm.member_id END
    )
  FROM descent d
  JOIN map_bounds.compilation_member cm ON cm.compilation_id = d.member_id
  WHERE _deep OR NOT map_bounds.holds_polygons(d.member_id)
)
SELECT member_id, coalesce(via, member_id) FROM descent
WHERE CASE
        WHEN _deep THEN NOT EXISTS (
          SELECT 1 FROM map_bounds.compilation_member c
          WHERE c.compilation_id = descent.member_id
        )
        -- A leaf is either something holding polygons or something with nothing
        -- beneath it. The second half matters for documentary members, which are
        -- the addressable units of a compilation whose content was ingested,
        -- despite holding no polygons of their own.
        ELSE map_bounds.holds_polygons(member_id)
          OR NOT EXISTS (
            SELECT 1 FROM map_bounds.compilation_member c
            WHERE c.compilation_id = descent.member_id
          )
      END;
$$ LANGUAGE SQL STABLE;

/** Which layer's faces represent a compilation.

  Faces are materialised per served layer, so a compilation that is not one has no
  faces of its own -- it borrows those of the layer it sits in, filtered to the
  maps it resolves to.
*/
CREATE OR REPLACE FUNCTION map_bounds.face_layer_for(_source_id integer)
  RETURNS integer AS $$
SELECT coalesce(
  (SELECT id FROM map_bounds.map_layer WHERE source_id = _source_id),
  (SELECT map_layer FROM map_bounds.map_area WHERE source_id = _source_id)
);
$$ LANGUAGE SQL STABLE;

/** Resolve a compilation by slug. Any compilation is addressable, not just the
  served layers the tile routes originally took. */
CREATE OR REPLACE FUNCTION map_bounds.compilation_id(_slug text)
  RETURNS integer AS $$
SELECT source_id FROM maps.sources WHERE slug = _slug;
$$ LANGUAGE SQL STABLE;

/** Compilation state: virtual, materialized, or stale. */
CREATE OR REPLACE VIEW map_bounds.compilation_sync AS
SELECT
  mc.compilation_id AS source_id,
  s.slug,
  count(*) AS n_members,
  coalesce(c.assembly_mode, 'layered') AS assembly_mode,
  c.content,
  map_bounds.holds_polygons(mc.compilation_id) AS materialized,
  c.member_hash,
  map_bounds.compilation_member_hash(mc.compilation_id) AS current_member_hash,
  CASE
    -- Members are provenance, not material: there is nothing to assemble, so the
    -- member hash says nothing and 'stale' would invite a destructive rebuild.
    WHEN c.content = 'ingested' THEN 'ingested'
    WHEN NOT map_bounds.holds_polygons(mc.compilation_id) THEN 'virtual'
    WHEN c.member_hash IS NOT DISTINCT FROM
         map_bounds.compilation_member_hash(mc.compilation_id) THEN 'current'
    ELSE 'stale'
  END AS state
FROM map_bounds.compilation_member mc
JOIN maps.sources s ON s.source_id = mc.compilation_id
LEFT JOIN map_bounds.compilation c ON c.source_id = mc.compilation_id
GROUP BY mc.compilation_id, s.slug, c.assembly_mode, c.content, c.member_hash;
