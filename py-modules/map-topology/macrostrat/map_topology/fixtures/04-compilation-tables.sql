/**
  COMPILATIONS

  A compilation is a map -- a `maps.sources` row assembled from other maps. It is
  not a distinct kind of thing, so there is no `map_type` column anywhere. Four
  facts classify a source, and there are no names for their combinations:

    is_compilation   has members                         (`compilation_member`)
    is_materialized  holds polygons of its own           (`maps.sources.is_finalized`)
    is_derived       those polygons are a cache cut from its members'
                                                         (read off the legend links)
    assembly_mode    topological | mosaic                (`compilation`, stored)

  So `bc-surface` is a materialized, derived, topological compilation; `sgmc` a
  materialized, non-derived mosaic; `medium` a virtual topological compilation.
  Two more facts are authored on `maps.sources`: `is_served` (may be requested by
  name) and `superseded_by`.
*/

CREATE TABLE IF NOT EXISTS map_bounds.compilation_member (
  compilation_id integer NOT NULL
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  member_id integer NOT NULL
    REFERENCES maps.sources(source_id) ON DELETE CASCADE,
  /** Higher wins where members overlap. NULL for a mosaic, where nothing
    overlaps and the ordering carries no meaning. */
  priority integer,
  PRIMARY KEY (compilation_id, member_id),
  CONSTRAINT compilation_member_no_self_reference
    CHECK (compilation_id != member_id)
);

/* Membership carries a priority and nothing else. `role` was an open vocabulary
   nothing read; the one value written (`snapshot`, on three edges of `carto-v1`)
   described the compilation, not the edges. */
ALTER TABLE map_bounds.compilation_member DROP COLUMN IF EXISTS role;

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
    extent in a compilation is whatever faces it wins -- the topology's job.

    `mosaic`: members partition the compilation and never overlap. A member's
    extent *is* its bounds, and its content is the compilation's content inside
    them (`content_of`). Nothing is noded for it and it owns no face -- unless a
    topological compilation contains it directly, at which point it is an
    ordinary map there. SGMC's 55 published maps are the case; a nested virtual
    mosaic (two South Carolina maps as one unit) is the same thing one level down.

    Not derivable -- whether members overlap is an assertion the operator makes. */
  assembly_mode text NOT NULL DEFAULT 'topological'
    CHECK (assembly_mode IN ('topological', 'mosaic')),
  /** The member set the compilation's derived polygons were built from. NULL
    while virtual; `is_stale` once it no longer matches the current members.

    Nothing records *whether* the polygons are derived: `materialize` writes each
    polygon with its member's legend entry, so a cache is recognisable from the
    rows themselves (`is_derived`), and `dematerialize` checks every polygon
    before it deletes anything. */
  member_hash uuid,
  note text
);
/* Bounds are composed by the `compile` opening operation now, which keeps its own
   staleness stamp in `boundary_op.parameters`. The view that read the column goes
   first. */
DROP VIEW IF EXISTS map_bounds.compilation_assembly;
ALTER TABLE map_bounds.compilation DROP COLUMN IF EXISTS assembly_hash;

/** THE FACE REGISTER

  `map_layer` is the topology library's register of the compilations whose
  faces are cached in `map_face`. It is not a second kind of thing: `large` is
  the compilation of all large-scale maps, `carto-large` the compilation of
  `medium` and `large`. The key stays `id` for now (the library's `map_face`,
  `face_identity` and `dirty_face` reference it); `source_id` is the bridge into
  the map world.
*/
ALTER TABLE map_bounds.map_layer
  ADD COLUMN IF NOT EXISTS source_id integer UNIQUE
    REFERENCES maps.sources(source_id) ON DELETE SET NULL;

/** Give every registered compilation a map identity, so it can hold and be
  held as a compilation member. */
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

/* ---------------------------------------------------------------------------
   PREDICATES -- the one vocabulary every consumer reads. Nothing inlines these.
   --------------------------------------------------------------------------- */

/** Has members. */
CREATE OR REPLACE FUNCTION map_bounds.is_compilation(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation_member WHERE compilation_id = _source_id
);
$$ LANGUAGE SQL STABLE;

/** Has its faces cached in `map_face` -- a row in the library's register. */
CREATE OR REPLACE FUNCTION map_bounds.has_faces(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.map_layer WHERE source_id = _source_id
);
$$ LANGUAGE SQL STABLE;

/** May be requested by name. Authored on `maps.sources`; a source that is not
  served still resolves inside every compilation it belongs to. */
CREATE OR REPLACE FUNCTION map_bounds.is_served(_source_id integer)
  RETURNS boolean AS $$
SELECT coalesce(is_served, true) FROM maps.sources WHERE source_id = _source_id;
$$ LANGUAGE SQL STABLE;

/** Members partition the compilation; see `assembly_mode`. */
CREATE OR REPLACE FUNCTION map_bounds.is_mosaic(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation c
  WHERE c.source_id = _source_id AND c.assembly_mode = 'mosaic'
);
$$ LANGUAGE SQL STABLE;

/** Belongs to a mosaic. Not parted out on the mosaic's account and owns no face
  there; its extent is its bounds. It may still belong to a topological
  compilation directly. */
CREATE OR REPLACE FUNCTION map_bounds.is_mosaic_member(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation_member cm
  WHERE cm.member_id = _source_id
    AND map_bounds.is_mosaic(cm.compilation_id)
);
$$ LANGUAGE SQL STABLE;

/** Holds polygons of its own. `is_finalized` is the cached `has_map_schema_data`
  flag (and `materialize` sets it), so this is a lookup rather than a scan of the
  partitioned polygon table. Where `content_of` stops walking; the leaf test for
  identity resolution is `has_content`, which also admits a mosaic member
  standing for its mosaic's polygons. */
CREATE OR REPLACE FUNCTION map_bounds.is_materialized(_source_id integer)
  RETURNS boolean AS $$
SELECT coalesce(is_finalized, false)
FROM maps.sources
WHERE source_id = _source_id;
$$ LANGUAGE SQL STABLE;

/** Whether a compilation's polygons are a cache cut from its members' -- written
  by `materialize`, removable by `dematerialize`. Read off the data rather than
  recorded: a derived polygon keeps its member's legend entry, so a derived
  compilation holds polygons and owns no `maps.legend` row of its own. A
  compilation that holds polygons *and* legend rows holds originals (SGMC), and
  its members are provenance rather than material. The per-polygon form of the
  same test is `dematerialize`'s precondition. */
CREATE OR REPLACE FUNCTION map_bounds.is_derived(_source_id integer)
  RETURNS boolean AS $$
SELECT map_bounds.is_materialized(_source_id)
  AND map_bounds.is_compilation(_source_id)
  AND NOT EXISTS (
    SELECT 1 FROM maps.legend l WHERE l.source_id = _source_id
  );
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

/** A derived compilation whose members have changed since its polygons were cut. */
CREATE OR REPLACE FUNCTION map_bounds.is_stale(_source_id integer)
  RETURNS boolean AS $$
SELECT map_bounds.is_derived(_source_id)
  AND (
    SELECT c.member_hash IS DISTINCT FROM map_bounds.compilation_member_hash(_source_id)
    FROM map_bounds.compilation c WHERE c.source_id = _source_id
  );
$$ LANGUAGE SQL STABLE;

/** Bounds that are the whole world, by assertion: the source opened its bounds
  with the `world` operation. A client does not zoom to it, and overlap tests
  leave it out. */
CREATE OR REPLACE FUNCTION map_bounds.is_global(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.boundary_op
  WHERE source_id = _source_id AND position = 0 AND operation = 'world'
);
$$ LANGUAGE SQL STABLE;

/** Resolve any source by slug. */
CREATE OR REPLACE FUNCTION map_bounds.source_id(_slug text)
  RETURNS integer AS $$
SELECT source_id FROM maps.sources WHERE slug = _slug;
$$ LANGUAGE SQL STABLE;

/* ---------------------------------------------------------------------------
   CONTENT -- where a source's polygons are.
   --------------------------------------------------------------------------- */

/** Where a source's content actually is, and the bounds to read it through.

  An ordinary map is its own content: `(itself, NULL)`. A mosaic member holds
  nothing; its content is the nearest materialized mosaic above it, read inside
  the member's own bounds -- `ST_Contains(bounds, ST_PointOnSurface(geom))`,
  which is exact because the bounds were derived as the coverage union of exactly
  those features. Nested mosaics walk further (`sgmc-sc001 -> sgmc-sc -> sgmc`),
  and the depth is invisible to a caller.

  Every consumer that once wrote `WHERE p.source_id = <map>` reads through this
  instead: the single-map tile query, the carto fill, `materialize`. No row means
  the source has no content anywhere -- a virtual topological compilation, or a
  mosaic member whose chain never reaches polygons -- which is what `has_content`
  tests. */
CREATE OR REPLACE FUNCTION map_bounds.content_of(_source_id integer)
  RETURNS TABLE (source_id integer, footprint geometry) AS $$
WITH RECURSIVE up AS (
  SELECT _source_id AS id, 0 AS depth
  UNION ALL
  SELECT cm.compilation_id, up.depth + 1
  FROM up
  JOIN map_bounds.compilation_member cm ON cm.member_id = up.id
  WHERE NOT map_bounds.is_materialized(up.id)
    AND map_bounds.is_mosaic(cm.compilation_id)
)
SELECT
  up.id,
  CASE WHEN up.depth = 0 THEN NULL
       ELSE (SELECT a.geometry FROM map_bounds.map_area a WHERE a.source_id = _source_id)
  END
FROM up
WHERE map_bounds.is_materialized(up.id)
ORDER BY up.depth
LIMIT 1;
$$ LANGUAGE SQL STABLE;

/** Can be a resolved map: materialized, or a mosaic member standing for a
  materialized mosaic. This, not `is_materialized`, is where the flattening
  stops -- a mosaic member in a topological compilation owns faces there and is
  filled through `content_of`, though it holds no polygons itself. */
CREATE OR REPLACE FUNCTION map_bounds.has_content(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (SELECT 1 FROM map_bounds.content_of(_source_id));
$$ LANGUAGE SQL STABLE;

/** The polygons a source shows, wherever they are held.

  The one place "which rows belong to this source" is answered. An ordinary map's
  own rows; a mosaic member's mosaic's rows inside its bounds; a nested mosaic's
  through however many hops `content_of` takes. `_within` narrows to a tile
  envelope or a face, in the polygons' SRID, and may be NULL.

  Plain SQL and STABLE so the planner inlines it into the calling query: the
  scale predicate then prunes `maps.polygons` to the content's partition, the
  GiST index serves `_within`, and the bounds reach `ST_Contains` as one repeated
  value, so PostGIS prepares it once. `maps.sources.scale` is free text, so the
  enum cast is guarded to real partition keys.

  For one source and one envelope only. Do not `LATERAL` it per face: the planner
  re-runs the mosaic walk per output row and loses the constant envelope. */
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

/** The lines a source shows. Same contract as `polygons_of`, and the same exact
  `ST_Contains` test, so ownership is symmetric with the polygons. The cost is
  edge noise: a line whose representative point falls on or a few metres outside
  the bounds is not shown -- 5 of Nevada's 54,602, all fault segments of
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

/** The per-polygon form of `is_derived`, run before `dematerialize` deletes
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

/* ---------------------------------------------------------------------------
   MEMBERSHIP -- walking the tree.
   --------------------------------------------------------------------------- */

/** The members of a compilation: direct, or every source below it at any depth. */
CREATE OR REPLACE FUNCTION map_bounds.members_of(
  _source_id integer,
  _recursive boolean DEFAULT false
)
  RETURNS TABLE (source_id integer) AS $$
WITH RECURSIVE descent AS (
  SELECT cm.member_id
  FROM map_bounds.compilation_member cm
  WHERE cm.compilation_id = _source_id
  UNION
  SELECT cm.member_id
  FROM descent d
  JOIN map_bounds.compilation_member cm ON cm.compilation_id = d.member_id
  WHERE _recursive
)
SELECT member_id FROM descent;
$$ LANGUAGE SQL STABLE;

/** The maps a compilation resolves to, and the member of it each belongs to.

  The descent stops where the content is (`has_content`): a materialized
  compilation is an answer in its own right, a virtual one is walked through, a
  mosaic member in the compilation stands for its mosaic's polygons. Every row's
  `map_id` is a resolved map; a source with nothing beneath it is one too.

  `member_id` is the member of the compilation asked about that the resolved map
  belongs to -- what a face is presented as by default. Intermediate compilations
  that only exist to build others are skipped: today that is the registered scale
  layers (`has_faces`), which nobody means to see -- from `carto-large` British
  Columbia is `bc-surface`, not `medium`. (`is_served` takes this role once the
  scale layers are marked unserved.) A source directly in the compilation is its
  own member.
*/
CREATE OR REPLACE FUNCTION map_bounds.resolved_maps(_source_id integer)
  RETURNS TABLE (map_id integer, member_id integer) AS $$
WITH RECURSIVE descent AS (
  SELECT
    cm.member_id AS source_id,
    CASE WHEN map_bounds.has_faces(cm.member_id) THEN NULL ELSE cm.member_id END
      AS member_id
  FROM map_bounds.compilation_member cm
  WHERE cm.compilation_id = _source_id
  UNION ALL
  SELECT
    cm.member_id,
    coalesce(
      d.member_id,
      CASE WHEN map_bounds.has_faces(cm.member_id) THEN NULL ELSE cm.member_id END
    )
  FROM descent d
  JOIN map_bounds.compilation_member cm ON cm.compilation_id = d.source_id
  WHERE NOT map_bounds.has_content(d.source_id)
)
SELECT source_id, coalesce(member_id, source_id)
FROM descent
WHERE map_bounds.has_content(source_id)
   OR NOT map_bounds.is_compilation(source_id);
$$ LANGUAGE SQL STABLE;

/** Which register entry's faces represent a source: its own if it has faces,
  else the base layer its bounds are registered in. Interim, until every served
  compilation has faces of its own. */
CREATE OR REPLACE FUNCTION map_bounds.face_layer_for(_source_id integer)
  RETURNS integer AS $$
SELECT coalesce(
  (SELECT id FROM map_bounds.map_layer WHERE source_id = _source_id),
  (SELECT map_layer FROM map_bounds.map_area WHERE source_id = _source_id)
);
$$ LANGUAGE SQL STABLE;

/* ---------------------------------------------------------------------------
   FLATTENED RESOLUTION
   --------------------------------------------------------------------------- */

/** `map_priority` is **entirely derived**. Every authored edge lives in
  `compilation_member`; this table is what `sync-priority-paths` produces from it,
  and it exists so identity resolution can be a single indexed lookup rather than
  a recursive walk. One row per registered compilation per resolved map.

  `priority_path` is a map's effective standing under the compilation: the
  priority of every edge on the way down, concatenated. Postgres compares arrays
  lexicographically, so resolution keeps its shape and only changes what it
  orders by. Where paths share a prefix the deeper one wins -- a member deeper in
  the tree is more specifically placed than one directly in the compilation.

  `member_id` is the member of the compilation the resolved map belongs to (see
  `resolved_maps`).
*/
ALTER TABLE map_bounds.map_priority
  ADD COLUMN IF NOT EXISTS priority_path integer[];
ALTER TABLE map_bounds.map_priority DROP COLUMN IF EXISTS derived;
ALTER TABLE map_bounds.map_priority DROP COLUMN IF EXISTS priority;
ALTER TABLE map_bounds.map_priority
  ADD COLUMN IF NOT EXISTS member_id integer REFERENCES maps.sources(source_id);

/** Carto composition. `carto-large` is the compilation of `medium` and `large`;
  higher priority wins where they overlap. Ordinary membership edges between
  compilations that happen to be registered. */
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

/* ---------------------------------------------------------------------------
   BOUNDS

   A compilation's bounds go through the same pipeline as a map's: a `compile`
   opening operation (the union of every noded source below it) or `world`, then
   ordinary boundary operations, composed by `bounds build` and refreshed by
   `topo update`. A compilation has no topogeometry of its own -- it is not
   parted out, and identity resolves a materialized one through its members
   (`topology_sources_of`). The hierarchical `composite_topo` layer, the
   `compilation_assembly` view and `compilation_face_elements` that did this by
   reference are gone; the `map-topo-pieces` migration drops the layer.
   --------------------------------------------------------------------------- */
DROP VIEW IF EXISTS map_bounds.compilation_assembly;
DROP FUNCTION IF EXISTS map_bounds.compilation_face_elements(integer);

/** Every registered compilation gets a `map_area` row and an opening operation at
  creation, so it has bounds before any sync: the global ones (`tiny`, `small`,
  `carto-*`) open with `world`, the scale layers with `compile`. Compilations made
  later get `compile` from `topo update`. */
INSERT INTO map_bounds.map_area (id, geometry, map_layer)
SELECT ml.source_id,
  CASE WHEN ml.slug IN ('tiny', 'small', 'carto-small', 'carto-medium', 'carto-large')
       THEN ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))
       ELSE ST_GeomFromText('MULTIPOLYGON EMPTY', 4326) END,
  NULL
FROM map_bounds.map_layer ml
WHERE ml.source_id IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO map_bounds.boundary_op (source_id, position, operation, note)
SELECT ml.source_id, 0,
  CASE WHEN ml.slug IN ('tiny', 'small', 'carto-small', 'carto-medium', 'carto-large')
       THEN 'world' ELSE 'compile' END,
  'Seeded with the compilation schema'
FROM map_bounds.map_layer ml
WHERE ml.source_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.boundary_op o
    WHERE o.source_id = ml.source_id AND o.position = 0
  );
-- No ON CONFLICT: `boundary_op_unique_position` is deferrable, which ON CONFLICT
-- cannot use as an arbiter; the NOT EXISTS above is the idempotence.

/* ---------------------------------------------------------------------------
   STATE
   --------------------------------------------------------------------------- */

/** Per compilation: how many members, how members combine, and the three
  content facts. Built from `compilation_member`, so a compilation with no members
  has no row. */
DROP VIEW IF EXISTS map_bounds.compilation_sync;
CREATE VIEW map_bounds.compilation_sync AS
SELECT
  mc.compilation_id AS source_id,
  s.slug,
  count(*) AS n_members,
  coalesce(c.assembly_mode, 'topological') AS assembly_mode,
  map_bounds.is_materialized(mc.compilation_id) AS is_materialized,
  map_bounds.is_derived(mc.compilation_id) AS is_derived,
  map_bounds.is_stale(mc.compilation_id) AS is_stale,
  c.member_hash,
  map_bounds.compilation_member_hash(mc.compilation_id) AS current_member_hash
FROM map_bounds.compilation_member mc
JOIN maps.sources s ON s.source_id = mc.compilation_id
LEFT JOIN map_bounds.compilation c ON c.source_id = mc.compilation_id
GROUP BY mc.compilation_id, s.slug, c.assembly_mode, c.member_hash;

/* Retired names. `schema sync` cannot drop what a fixture no longer declares. */
DROP FUNCTION IF EXISTS map_bounds.holds_polygons(integer);
DROP FUNCTION IF EXISTS map_bounds.is_served_layer(integer);
DROP FUNCTION IF EXISTS map_bounds.compilation_id(text);
DROP FUNCTION IF EXISTS map_bounds.compilation_leaves(integer, boolean);
ALTER TABLE map_bounds.map_priority DROP COLUMN IF EXISTS via;
