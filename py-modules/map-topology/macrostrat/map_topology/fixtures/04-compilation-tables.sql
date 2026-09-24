/**
  COMPILATIONS

  A compilation is a map -- a `maps.sources` row assembled from other maps. It is
  not a distinct kind of thing, so there is no `map_type` column anywhere:
  "is a compilation" means *has members*, "is a constituent" means *is a member*,
  and both are read straight off `compilation_member`. Whether a map holds polygons
  of its own (`holds_polygons`) separates a concrete node from a virtual one; whether
  those polygons are a cache of its members' (`is_materialized`, read off the legend
  links `materialize` writes) separates a materialized compilation from an ingested
  one such as SGMC.
*/

CREATE TABLE IF NOT EXISTS map_bounds.compilation_member (
  compilation_id integer NOT NULL
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  member_id integer NOT NULL
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  /** Higher wins where members overlap. NULL for a mosaic, where nothing
    overlaps and the ordering carries no meaning. */
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
  /** How members' extents are settled.

    `topological`: members may overlap, priority resolves them, and a member's
    extent in a layer is whatever faces it wins -- the topology's job.

    `mosaic`: members partition the compilation's territory and never overlap. A
    member's extent *is* its footprint, and its content is the compilation's
    content inside that footprint (`content_of`). Nothing is noded for it, it
    owns no face, and it costs the topology nothing -- unless something
    topological places it directly, at which point it is an ordinary map there.
    SGMC's 55 published maps are the case; a nested virtual mosaic (two South
    Carolina maps as one unit) is the same thing one level down.

    Not derivable -- whether members overlap is an assertion the operator makes. */
  assembly_mode text NOT NULL DEFAULT 'topological'
    CHECK (assembly_mode IN ('topological', 'mosaic')),
  /** The member set the compilation's derived polygons were built from. NULL
    while virtual; stale once it no longer matches the current members.

    Nothing records *whether* the polygons are derived: `materialize` writes each
    polygon with its member's legend entry and the member's `map_id` as
    `orig_id`, so a cache is recognisable from the rows themselves
    (`is_materialized`), and `dematerialize` checks every polygon before it
    deletes anything. */
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
  compilation member. Layers hold no polygons and stand for none, so they are
  never an answer to identity resolution -- see `has_content` below. */
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


/** Whether a compilation's members partition its territory, so that each one's
  extent is its footprint rather than a set of faces. See `assembly_mode`. */
CREATE OR REPLACE FUNCTION map_bounds.is_mosaic(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation c
  WHERE c.source_id = _source_id AND c.assembly_mode = 'mosaic'
);
$$ LANGUAGE SQL STABLE;

/** Whether a map is a member of a mosaic. Such a map is not parted out into the
  topology on the mosaic's account and owns no face there; its extent is its
  footprint. It may still be placed in a topological compilation directly. */
CREATE OR REPLACE FUNCTION map_bounds.is_mosaic_member(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation_member cm
  WHERE cm.member_id = _source_id
    AND map_bounds.is_mosaic(cm.compilation_id)
);
$$ LANGUAGE SQL STABLE;

/** Whether a map holds polygons of its own. This is where `content_of` stops
  walking; the leaf test for identity resolution is `has_content`, which also
  admits a mosaic member standing for its parent's polygons. `is_finalized` is the
  cached `has_map_schema_data` flag (and `materialize` sets it), so this is a lookup
  rather than a scan of the partitioned polygon table. */
CREATE OR REPLACE FUNCTION map_bounds.holds_polygons(_source_id integer)
  RETURNS boolean AS $$
SELECT coalesce(is_finalized, false)
FROM maps.sources
WHERE source_id = _source_id;
$$ LANGUAGE SQL STABLE;

/** Where a map's content actually is, and the footprint to read it through.

  An ordinary map is its own content: `(itself, NULL)`. A mosaic member holds
  nothing; its content is the nearest ancestor up the mosaic edges that does,
  read inside the member's own footprint -- `ST_Contains(footprint,
  ST_PointOnSurface(geom))`, which is exact because the footprint was derived
  as the coverage union of exactly those features. Nested mosaics walk further
  (`sgmc-sc001 -> sgmc-sc -> sgmc`), and the depth is invisible to a caller.

  Every consumer that once wrote `WHERE p.source_id = <map>` reads through this
  instead: the single-map tile query, the carto fill, `materialize`. No row means
  the map has no content anywhere -- a virtual topological compilation, or a mosaic
  member whose chain never reaches polygons -- which is what `has_content` tests. */
CREATE OR REPLACE FUNCTION map_bounds.content_of(_source_id integer)
  RETURNS TABLE (source_id integer, footprint geometry) AS $$
WITH RECURSIVE up AS (
  SELECT _source_id AS id, 0 AS depth
  UNION ALL
  SELECT cm.compilation_id, up.depth + 1
  FROM up
  JOIN map_bounds.compilation_member cm ON cm.member_id = up.id
  WHERE NOT map_bounds.holds_polygons(up.id)
    AND map_bounds.is_mosaic(cm.compilation_id)
)
SELECT
  up.id,
  CASE WHEN up.depth = 0 THEN NULL
       ELSE (SELECT a.geometry FROM map_bounds.map_area a WHERE a.source_id = _source_id)
  END
FROM up
WHERE map_bounds.holds_polygons(up.id)
ORDER BY up.depth
LIMIT 1;
$$ LANGUAGE SQL STABLE;

/** Whether a map is a leaf for identity resolution: it has content of its own,
  or content it can stand for through a mosaic. This, not `holds_polygons`, is
  where the flattening stops -- a mosaic member placed in a layer owns faces and
  is filled through `content_of`, though it holds no polygons itself. */
CREATE OR REPLACE FUNCTION map_bounds.has_content(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (SELECT 1 FROM map_bounds.content_of(_source_id));
$$ LANGUAGE SQL STABLE;

/** The polygons a map shows, wherever they are held.

  The one place "which rows belong to this map" is answered. An ordinary map's
  own rows; a mosaic member's parent's rows inside its footprint; a nested
  mosaic's through however many hops `content_of` takes. `_within` narrows to a
  tile envelope or a face, in the polygons' SRID, and may be NULL.

  Plain SQL and STABLE so the planner inlines it into the calling query: the
  scale predicate then prunes `maps.polygons` to the content's partition, the
  GiST index serves `_within`, and the footprint reaches `ST_Contains` as one
  repeated value, so PostGIS prepares it once. `maps.sources.scale` is free
  text, so the enum cast is guarded to real partition keys.

  Callers: the single-map tile queries, the carto fill, `materialize`. Anything
  else that would write `WHERE p.source_id = <map>` belongs here instead. */
CREATE OR REPLACE FUNCTION map_bounds.polygons_of(
  _source_id integer,
  _within geometry DEFAULT NULL
)
  RETURNS SETOF maps.polygons AS $$
SELECT p.*
FROM map_bounds.content_of(_source_id) c
JOIN maps.sources cs
  ON cs.source_id = c.source_id
 AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
JOIN maps.polygons p
  ON p.source_id = c.source_id
 AND p.scale = cs.scale::maps.map_scale
WHERE (_within IS NULL OR ST_Intersects(p.geom, _within))
  AND (c.footprint IS NULL OR ST_Contains(c.footprint, ST_PointOnSurface(p.geom)));
$$ LANGUAGE SQL STABLE;

/** The lines a map shows. Same contract as `polygons_of`, and the same exact
  `ST_Contains` test, so ownership is symmetric with the polygons. The cost is
  edge noise: a line whose representative point falls on or a few metres outside
  the footprint edge is not shown -- 5 of Nevada's 54,602, all fault segments of
  0.1-0.3 km. `ST_Intersects` would recover 3 of them and add 9 of the
  neighbours' lines along the shared border, which is not better. */
CREATE OR REPLACE FUNCTION map_bounds.lines_of(
  _source_id integer,
  _within geometry DEFAULT NULL
)
  RETURNS SETOF maps.lines AS $$
SELECT l.*
FROM map_bounds.content_of(_source_id) c
JOIN maps.sources cs
  ON cs.source_id = c.source_id
 AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
JOIN maps.lines l
  ON l.source_id = c.source_id
 AND l.scale = cs.scale::maps.map_scale
WHERE (_within IS NULL OR ST_Intersects(l.geom, _within))
  AND (c.footprint IS NULL OR ST_Contains(c.footprint, ST_PointOnSurface(l.geom)));
$$ LANGUAGE SQL STABLE;

/** Whether a compilation's polygons are a cache of its members' -- written by
  `materialize`, removable by `dematerialize`. Read off the data rather than
  recorded: a derived polygon keeps its member's legend entry, so a materialized
  compilation holds polygons and owns no `maps.legend` row of its own. A
  compilation that holds polygons *and* legend rows holds originals (SGMC), and
  its members are provenance rather than material. The per-polygon form of the
  same test is `dematerialize`'s precondition. */
CREATE OR REPLACE FUNCTION map_bounds.is_materialized(_source_id integer)
  RETURNS boolean AS $$
SELECT map_bounds.holds_polygons(_source_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = _source_id
  )
  AND NOT EXISTS (
    SELECT 1 FROM maps.legend l WHERE l.source_id = _source_id
  );
$$ LANGUAGE SQL STABLE;

/** The per-polygon form of `is_materialized`, run before `dematerialize` deletes
  anything: every polygon must carry a legend entry owned by some *other* source
  (the member it was cut from), which is what `materialize` writes and an
  ingested dataset never has. One polygon that fails -- unlinked, or linked to a
  legend row the compilation itself owns, as all of SGMC's are -- and the whole
  call raises. */
CREATE OR REPLACE FUNCTION map_bounds.assert_dematerializable(_source_id integer)
  RETURNS void AS $$
DECLARE
  _bad integer;
  _total integer;
BEGIN
  SELECT
    count(*) FILTER (WHERE NOT EXISTS (
      SELECT 1
      FROM maps.map_legend ml
      JOIN maps.legend l ON l.legend_id = ml.legend_id
      WHERE ml.map_id = p.map_id
        AND l.source_id <> p.source_id
    )),
    count(*)
  INTO _bad, _total
  FROM maps.polygons p
  WHERE p.source_id = _source_id;

  IF _bad > 0 THEN
    RAISE EXCEPTION USING
      MESSAGE = 'Refusing to dematerialize source ' || _source_id || ': ' || _bad
        || ' of ' || _total || ' polygons are not linked to another source''s'
        || ' legend, so they cannot be shown to be a cache of the members'' polygons.';
  END IF;
END;
$$ LANGUAGE plpgsql STABLE;

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
-- Dropped rather than replaced: `face_elements` moved out to
-- `compilation_face_elements()`, and `CREATE OR REPLACE VIEW` cannot drop a
-- column, so replacing in place fails on any database built before that split.
-- Nothing else selects from this view, so the drop needs no CASCADE.
DROP VIEW IF EXISTS map_bounds.compilation_assembly;
CREATE VIEW map_bounds.compilation_assembly AS
WITH RECURSIVE descendants AS (
  -- A mosaic is not assembled from anything: its boundary is its own (authored,
  -- or derived once from its members' footprints) and its members are never
  -- noded, so there is nothing to reference. Excluding it here is what keeps
  -- every consumer of this view -- boundary read-back, `face_elements`,
  -- staleness -- from clearing a boundary nothing would rebuild.
  SELECT cm.compilation_id AS root, cm.member_id
  FROM map_bounds.compilation_member cm
  WHERE NOT map_bounds.is_mosaic(cm.compilation_id)
  UNION
  SELECT d.root, cm.member_id
  FROM descendants d
  JOIN map_bounds.compilation_member cm
    ON cm.compilation_id = d.member_id
  -- Stop at a map that has content: it is a leaf, not a container. A mosaic
  -- placed here counts as content and is not descended into.
  WHERE NOT map_bounds.has_content(d.member_id)
)
SELECT
  d.root AS source_id,
  -- References to the members' own topogeometries, for the hierarchical layer.
  array_agg(DISTINCT ARRAY[(a.topo).id, (a.topo).layer_id]) AS elements,
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
LEFT JOIN map_bounds.compilation c ON c.source_id = d.root
GROUP BY d.root, c.assembly_hash;


/** The primitive faces a compilation's members cover, as `createTopoGeom`
  elements.

  A *materialized* compilation needs a level-0 topogeometry, because
  `identity_for_face` resolves there and a compilation cannot own a face without
  one. Assembled by reference: its boundary is already in the topology as its
  members' edges, and re-noding a simplified transform of it fails where the
  simplified line crosses an edge it should have followed.

  Deliberately *not* a column of `compilation_assembly`. It requires joining every
  member's face relations, which on a real corpus is millions of rows -- 4.0M
  across 14 compilations here, 488k in the largest -- and takes about 8 s, where
  the rest of that view answers in 65 ms. The view is evaluated for every
  compilation on every run to decide staleness; these elements are needed only for
  the rare compilation actually being built, so they are resolved per call
  instead. */
CREATE OR REPLACE FUNCTION map_bounds.compilation_face_elements(_source_id integer)
  RETURNS integer[][] AS $$
WITH RECURSIVE descendants AS (
  SELECT cm.member_id
  FROM map_bounds.compilation_member cm
  WHERE cm.compilation_id = _source_id
    AND NOT map_bounds.is_mosaic(cm.compilation_id)
  UNION
  SELECT cm.member_id
  FROM descendants d
  JOIN map_bounds.compilation_member cm
    ON cm.compilation_id = d.member_id
  WHERE NOT map_bounds.has_content(d.member_id)
)
SELECT array_agg(DISTINCT ARRAY[r.element_id, 3])
FROM descendants d
JOIN map_bounds.map_area a
  ON a.source_id = d.member_id
 AND a.topo IS NOT NULL
JOIN map_bounds_topology.relation r
  ON r.layer_id = (a.topo).layer_id
 AND r.topogeo_id = (a.topo).id
 AND r.element_type = 3;
$$ LANGUAGE sql STABLE;

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
  WHERE _deep OR NOT map_bounds.has_content(d.member_id)
)
SELECT member_id, coalesce(via, member_id) FROM descent
WHERE CASE
        WHEN _deep THEN NOT EXISTS (
          SELECT 1 FROM map_bounds.compilation_member c
          WHERE c.compilation_id = descent.member_id
        )
        -- A leaf is either something with content -- its own, or a mosaic's
        -- through its footprint -- or something with nothing beneath it.
        ELSE map_bounds.has_content(member_id)
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

/** Polygon-cache state per compilation: `virtual` (no polygons of its own),
  `ingested` (holds polygons that are originals, not a cache), `current` or
  `stale` (a cache whose `member_hash` does or does not match the membership
  now). Built from `compilation_member`, so a compilation with no members has no
  row. */
CREATE OR REPLACE VIEW map_bounds.compilation_sync AS
SELECT
  mc.compilation_id AS source_id,
  s.slug,
  count(*) AS n_members,
  coalesce(c.assembly_mode, 'topological') AS assembly_mode,
  map_bounds.holds_polygons(mc.compilation_id) AS holds_polygons,
  map_bounds.is_materialized(mc.compilation_id) AS is_materialized,
  c.member_hash,
  map_bounds.compilation_member_hash(mc.compilation_id) AS current_member_hash,
  CASE
    WHEN NOT map_bounds.holds_polygons(mc.compilation_id) THEN 'virtual'
    -- Originals: there is nothing to assemble, so the member hash says nothing
    -- and 'stale' would invite a destructive rebuild.
    WHEN NOT map_bounds.is_materialized(mc.compilation_id) THEN 'ingested'
    WHEN c.member_hash IS NOT DISTINCT FROM
         map_bounds.compilation_member_hash(mc.compilation_id) THEN 'current'
    ELSE 'stale'
  END AS state
FROM map_bounds.compilation_member mc
JOIN maps.sources s ON s.source_id = mc.compilation_id
LEFT JOIN map_bounds.compilation c ON c.source_id = mc.compilation_id
GROUP BY mc.compilation_id, s.slug, c.assembly_mode, c.member_hash;
