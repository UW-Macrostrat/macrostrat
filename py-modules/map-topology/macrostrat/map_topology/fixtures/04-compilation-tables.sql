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

    `multiscale`: members are alternatives by scale, not overlapping layers of
    one surface -- at most one member per scale. A request at a zoom is answered
    by the member whose scale band contains it (`serving_source`); nothing is
    noded, no faces are solved, and priority is meaningless (NULL). Laying out
    faces within a scale is the member's job, so that member is a topological
    compilation of its own. `carto` is the case: one source naming the whole
    tree `tiny` / `carto-small` / `carto-medium` / `carto-large`, so a
    compilation stays a zoom-independent identity and only this mode delegates
    by zoom.

    Not derivable -- whether members overlap is an assertion the operator makes. */
  assembly_mode text NOT NULL DEFAULT 'topological'
    CHECK (assembly_mode IN ('topological', 'mosaic', 'multiscale')),
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

  `map_layer` is the topology library's register: one row per solved layer,
  keyed by the compilation it belongs to. Every topological compilation with
  members and no content of its own is solved, served or not
  (`solved_compilations`); sync creates and removes the rows. A multiscale
  compilation has no layer: its faces at a zoom are those of its member at that
  scale (`face_layer_for`).

  One more row has no compilation: the *barrier layer* (`barrier_layer`), in
  which every noded map's boundary is recorded (`map_area.map_layer`). It is
  never solved, and every solved layer composes it, which is how a map's bounds
  are a barrier in each layer that solves it.

  The key stays `id` (the library's `map_face`, `face_identity` and `dirty_face`
  reference it). A layer is named by its compilation; the `slug` column is no
  longer read.
*/
/* A layer goes with its compilation, and its faces, rankings and composition
   with it -- what sync would remove anyway. Setting the source NULL instead
   would collide with the barrier layer's, the one row the key allows without a
   compilation. */
ALTER TABLE map_bounds.map_layer
  ADD COLUMN IF NOT EXISTS source_id integer
    REFERENCES maps.sources(source_id) ON DELETE CASCADE;
ALTER TABLE map_bounds.map_layer
  ADD CONSTRAINT map_layer_source_id_key UNIQUE NULLS NOT DISTINCT (source_id);

/** The barrier layer: the one row without a compilation, which the key allows
  only once. Topological, because the library keeps
  barriers only for topological layers. */
INSERT INTO map_bounds.map_layer (name, topological)
VALUES ('Boundaries', true)
ON CONFLICT (source_id) DO NOTHING;

CREATE OR REPLACE FUNCTION map_bounds.barrier_layer()
  RETURNS integer AS $$
SELECT id FROM map_bounds.map_layer WHERE source_id IS NULL;
$$ LANGUAGE SQL STABLE;

/** The compilations the carto tree is built from. Unserved: each exists to
  build `carto`, which is what is requested by name, and each is solved as a
  layer of its own. Inserted once; `is_served` is authored from then on. */
INSERT INTO maps.sources (slug, name, status_code, is_finalized, is_served)
VALUES
  ('tiny', 'Tiny', 'active', false, false),
  ('small', 'Small', 'active', false, false),
  ('medium', 'Medium', 'active', false, false),
  ('large', 'Large', 'active', false, false),
  ('carto-small', 'Carto small', 'active', false, false),
  ('carto-medium', 'Carto medium', 'active', false, false),
  ('carto-large', 'Carto large', 'active', false, false)
ON CONFLICT (slug) DO NOTHING;

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

/** Has faces of its own: a solved layer, which is one with rankings. */
CREATE OR REPLACE FUNCTION map_bounds.has_faces(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1
  FROM map_bounds.map_layer ml
  JOIN map_bounds.map_priority mp ON mp.map_layer = ml.id
  WHERE ml.source_id = _source_id
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
/** Members are alternatives by scale; see `assembly_mode` and `serving_source`. */
CREATE OR REPLACE FUNCTION map_bounds.is_multiscale(_source_id integer)
  RETURNS boolean AS $$
SELECT EXISTS (
  SELECT 1 FROM map_bounds.compilation c
  WHERE c.source_id = _source_id AND c.assembly_mode = 'multiscale'
);
$$ LANGUAGE SQL STABLE;

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

/** A source named the way a route names it: a slug, or an integer id as text
  (v2's `source_id`). NULL when there is no such source. */
CREATE OR REPLACE FUNCTION map_bounds.resolve_source(_ident text)
  RETURNS integer AS $$
SELECT CASE
  WHEN _ident ~ '^[0-9]+$' THEN
    (SELECT s.source_id FROM maps.sources s WHERE s.source_id = _ident::integer)
  ELSE map_bounds.source_id(_ident)
END;
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
  belongs to -- what a face is presented as by default. Unserved compilations,
  which exist only to build others, are skipped -- from `carto` British Columbia
  is `bc-surface`, not `carto-large` or `medium`. A source directly in the
  compilation is its own member.
*/
CREATE OR REPLACE FUNCTION map_bounds.resolved_maps(_source_id integer)
  RETURNS TABLE (map_id integer, member_id integer) AS $$
WITH RECURSIVE descent AS (
  SELECT
    cm.member_id AS source_id,
    CASE WHEN map_bounds.is_served(cm.member_id) THEN cm.member_id END
      AS member_id
  FROM map_bounds.compilation_member cm
  WHERE cm.compilation_id = _source_id
  UNION ALL
  SELECT
    cm.member_id,
    coalesce(
      d.member_id,
      CASE WHEN map_bounds.is_served(cm.member_id) THEN cm.member_id END
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
  higher priority wins where they overlap. Ordinary membership edges. */
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
JOIN maps.sources parent ON parent.slug = v.parent_slug
JOIN maps.sources member ON member.slug = v.member_slug
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

/* Every registered compilation gets a `map_area` row and an opening operation --
   the global ones (`tiny`, `small`, `carto-*`) open with `world`, the scale
   layers with `compile`. That is data, which the schema differ does not carry,
   so it lives in `bounds/layers.py`: `create_topo_fixtures` seeds a fresh
   database with it and the `compilation-layer-bounds` migration an existing one.
   Compilations made later get `compile` from `topo update`. */

/* ---------------------------------------------------------------------------
   SCALE BANDS -- the one place zoom thresholds live.

   Each `maps.map_scale` value owns the zooms from its `min_zoom` up to the next
   band's. Contiguous by construction, so there is nothing to keep consistent:
   `tiny` must start at 0 and the last band runs to any zoom. These replace the
   3/6/9 constants that the tileserver, the cache manager, v2 and v3 each kept
   a copy of, and `map_layer.min_zoom` / `max_zoom`, which disagreed with them.
   --------------------------------------------------------------------------- */
CREATE TABLE IF NOT EXISTS map_bounds.scale_band (
  scale maps.map_scale PRIMARY KEY,
  min_zoom integer NOT NULL CHECK (min_zoom >= 0)
);

/* The legacy build's bands. A z6 tile over the Midwest holds 11-21M vertices of
   medium-scale state maps (4-6 s to draw uncached); starting `medium` at 7 draws
   it from the small-scale maps in under 0.3 s, and is one UPDATE away when that
   trade is wanted. Seeded once. */
INSERT INTO map_bounds.scale_band (scale, min_zoom)
VALUES ('tiny', 0), ('small', 3), ('medium', 6), ('large', 9)
ON CONFLICT (scale) DO NOTHING;

/** The scale band a zoom falls in. Zooms below 0 read as 0. */
CREATE OR REPLACE FUNCTION map_bounds.scale_for_zoom(_zoom integer)
  RETURNS maps.map_scale AS $$
SELECT scale
FROM map_bounds.scale_band
WHERE greatest(_zoom, 0) >= min_zoom
ORDER BY min_zoom DESC
LIMIT 1;
$$ LANGUAGE SQL STABLE;

/** The zooms a source is drawn at when requested by name: from its scale
  band's first zoom to two past its last, beyond which a client overzooms the
  last tiles. Below the band a tile holds far more detail than it can show -- a
  z2 tile of the NGS state maps is every one of them at full resolution -- so
  none is drawn there.

  A compilation's range is its own designated scale's, whatever its members'
  are: `large` is drawn from z9, its medium-scale gap-filler with it, and that
  map is seen at lower zooms by requesting it directly or through a compilation
  drawn there. Only a source without a scale -- `carto`, which is multiscale --
  spans its members'.
  `max_zoom` is NULL for the last band, which runs to any zoom; both are NULL
  for a source with no scale anywhere below it, which is drawn at every zoom. */
CREATE OR REPLACE FUNCTION map_bounds.zoom_range(_source_id integer)
  RETURNS TABLE (min_zoom integer, max_zoom integer) AS $$
WITH RECURSIVE down AS (
  SELECT _source_id AS id, ARRAY[_source_id] AS seen
  UNION ALL
  SELECT cm.member_id, d.seen || cm.member_id
  FROM down d
  JOIN maps.sources s ON s.source_id = d.id
  JOIN map_bounds.compilation_member cm ON cm.compilation_id = d.id
  WHERE NOT coalesce(s.scale = ANY (enum_range(NULL::maps.map_scale)::text[]), false)
    AND NOT cm.member_id = ANY (d.seen)
),
bands AS (
  SELECT
    sb.min_zoom,
    (SELECT min(nb.min_zoom) - 1
     FROM map_bounds.scale_band nb
     WHERE nb.min_zoom > sb.min_zoom) AS max_zoom
  FROM down d
  JOIN maps.sources s ON s.source_id = d.id
  JOIN map_bounds.scale_band sb ON sb.scale::text = s.scale
)
SELECT
  min(min_zoom),
  CASE WHEN bool_or(max_zoom IS NULL) THEN NULL ELSE max(max_zoom) + 2 END
FROM bands;
$$ LANGUAGE SQL STABLE;

/* ---------------------------------------------------------------------------
   SERVING -- what a request for a source, at a zoom, is answered from.

   Every route (tiles, v2 point lookup, v3 units) resolves through these and
   carries no zoom logic of its own. Each is called ONCE per request with
   constant arguments; none of them is to be joined `LATERAL` per row, for the
   reason `polygons_of` gives.
   --------------------------------------------------------------------------- */

/** The source that answers for `_source_id` at `_zoom`: a multiscale
  compilation delegates to its member at the zoom's scale, recursively; anything
  else answers for itself. A multiscale compilation has at most one member per
  scale -- checked where membership is written (the compilation editor) and by
  `lint`, since the rule reads the members' own `scale`, which changes without
  the membership changing. One with no member for the scale answers for itself,
  and as a virtual compilation without faces that is nothing. */
CREATE OR REPLACE FUNCTION map_bounds.serving_source(_source_id integer, _zoom integer)
  RETURNS integer AS $$
WITH RECURSIVE down AS (
  SELECT _source_id AS id, 0 AS depth
  UNION ALL
  SELECT cm.member_id, down.depth + 1
  FROM down
  JOIN map_bounds.compilation_member cm ON cm.compilation_id = down.id
  JOIN maps.sources m ON m.source_id = cm.member_id
  WHERE map_bounds.is_multiscale(down.id)
    AND m.scale = map_bounds.scale_for_zoom(_zoom)::text
)
SELECT id FROM down ORDER BY depth DESC LIMIT 1;
$$ LANGUAGE SQL STABLE;

/** Solved into a layer of its own: a topological compilation with members and
  no content of its own, served or not. A mosaic's content is its members'
  polygons and a materialized compilation's is its own, so neither needs faces;
  a multiscale compilation draws its members' (`face_layer_for`). */
CREATE OR REPLACE FUNCTION map_bounds.is_solved(_source_id integer)
  RETURNS boolean AS $$
SELECT map_bounds.is_compilation(_source_id)
  AND NOT map_bounds.is_mosaic(_source_id)
  AND NOT map_bounds.is_multiscale(_source_id)
  AND NOT map_bounds.has_content(_source_id);
$$ LANGUAGE SQL STABLE;

/** The layer whose faces are drawn for a source at a zoom: that of the source
  answering at the zoom (`serving_source`) -- the source's own, or for a
  multiscale compilation its member's at the zoom's scale. NULL for a source
  without faces: a map, a materialized compilation, a mosaic. */
DROP FUNCTION IF EXISTS map_bounds.face_layer_for(integer);
CREATE OR REPLACE FUNCTION map_bounds.face_layer_for(
  _source_id integer,
  _zoom integer DEFAULT NULL
)
  RETURNS integer AS $$
SELECT ml.id
FROM map_bounds.map_layer ml
WHERE ml.source_id = map_bounds.serving_source(_source_id, _zoom)
  -- Solved: a layer without rankings has no faces.
  AND EXISTS (SELECT 1 FROM map_bounds.map_priority mp WHERE mp.map_layer = ml.id);
$$ LANGUAGE SQL STABLE;


/** The mapped polygons of a source at a location: which rows of `maps.polygons`
  a request for `_ident` at `_zoom` should read within `_within`.

  Resolution, in order:
    - `sys\:carto-legacy` reads the legacy `carto.polygons` build at the zoom's
      scale. A reserved name, never a `maps.sources` row: it exists so the
      compilation system can be measured against the materialized build on the
      same routes while both are served, and goes with Stage D.
    - otherwise `_ident` (slug or id) is resolved;
    - a source with faces -- for a multiscale one, its member's at the zoom
      (`face_layer_for`) -- resolves in two phases: its `map_face` coverage,
      then one indexed lookup per face for that map's content -- exactly the
      shape `carto-dynamic.sql` and v3's `units.sql` had inline;
    - anything else reads `polygons_of` of the source answering at the zoom
      (`serving_source`, the multiscale hop): a map, a mosaic member, a
      materialized compilation. A virtual compilation without faces returns
      nothing.

  `source_id` is the content holder (the map whose row it is); `member_id` is
  the member of the served compilation the face's map belongs to, and
  `priority_path` its rank there. Both are NULL outside a face. The priority is
  looked up by the face's owner, not the content holder: a mosaic member placed
  in a layer owns the face while SGMC holds the polygons.

  Only keys come back. Names, legend text and intervals are the caller's
  decoration, which v2 and v3 do differently and over at most a handful of rows. */
CREATE OR REPLACE FUNCTION map_bounds.units_at(
  _ident text,
  _within geometry,
  _zoom integer
)
  RETURNS TABLE (
    map_id integer,
    source_id integer,
    scale maps.map_scale,
    map_layer_id integer,
    map_face_id integer,
    member_id integer,
    priority_path integer[]
  ) AS $$
DECLARE
  _source integer;
  _target integer;
  _layer integer;
BEGIN
  IF _ident = 'sys\:carto-legacy' THEN
    RETURN QUERY
    SELECT
      p.map_id,
      p.source_id,
      CAST(p.geom_scale AS maps.map_scale),
      NULL::integer, NULL::integer, NULL::integer, NULL::integer[]
    FROM carto.polygons p
    WHERE p.scale = map_bounds.scale_for_zoom(_zoom)
      AND ST_Intersects(p.geom, _within);
    RETURN;
  END IF;

  _source := map_bounds.resolve_source(_ident);
  _target := map_bounds.serving_source(_source, _zoom);
  IF _target IS NULL THEN
    RETURN;
  END IF;

  -- The faces are `_target`'s; without faces, its own polygons (or lines) are
  -- read.
  _layer := map_bounds.face_layer_for(_source, _zoom);

  IF _layer IS NULL THEN
    RETURN QUERY
    SELECT
      p.map_id,
      p.source_id,
      p.scale,
      NULL::integer, NULL::integer, NULL::integer, NULL::integer[]
    FROM map_bounds.polygons_of(_target, _within) p;
    RETURN;
  END IF;

  RETURN QUERY
  WITH faces AS MATERIALIZED (
    SELECT mf.id AS face_id, mf.map_id AS owner_id
    FROM map_bounds_topology.map_face mf
    WHERE mf.map_layer = _layer
      AND ST_Intersects(mf.geometry, _within)
  ),
  /* Where each face's map keeps its polygons, resolved once per face. */
  holders AS MATERIALIZED (
    SELECT
      f.face_id,
      f.owner_id,
      c.source_id AS content_id,
      c.footprint,
      cs.scale AS content_scale
    FROM faces f
    CROSS JOIN LATERAL map_bounds.content_of(f.owner_id) c
    JOIN maps.sources cs
      ON cs.source_id = c.source_id
     AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  )
  SELECT
    p.map_id,
    p.source_id,
    p.scale,
    _layer,
    h.face_id,
    mp.member_id,
    mp.priority_path
  FROM holders h
  JOIN maps.polygons p
    ON p.source_id = h.content_id
   AND p.scale = CAST(h.content_scale AS maps.map_scale)
   AND ST_Intersects(p.geom, _within)
  LEFT JOIN map_bounds.map_priority mp
    ON mp.map_layer = _layer
   AND mp.map_id = h.owner_id
  /* The face bounds what its map answers for: an area request can span several
     faces, and a map's polygons must not be reported where another map's face
     covers them. Fetched by id, tested against the representative point. */
  WHERE EXISTS (
      SELECT 1 FROM map_bounds_topology.map_face f
      WHERE f.id = h.face_id
        AND ST_Contains(f.geometry, ST_PointOnSurface(p.geom))
    )
    AND (h.footprint IS NULL OR ST_Contains(h.footprint, ST_PointOnSurface(p.geom)));
END;
/* `ROWS`: a point resolves to one or a few polygons, and the planner's default
   estimate of 1000 for a set-returning function made every caller that
   decorated the keys hash-join whole tables -- `map_legend` (3.5M rows),
   `sources`, `legend` -- for a one-row answer: ~1 s in v2 against 7 ms with the
   estimate right. An area request gets nested-loop index lookups per row, which
   is what it wants too. */
$$ LANGUAGE plpgsql STABLE ROWS 20;

/** The lines of a source at a location; the `maps.lines` counterpart of
  `units_at`, resolved the same way. A line is reported where it intersects a
  face of the served compilation, as the tiles draw it. */
CREATE OR REPLACE FUNCTION map_bounds.lines_at(
  _ident text,
  _within geometry,
  _zoom integer
)
  RETURNS TABLE (
    line_id integer,
    source_id integer,
    scale maps.map_scale,
    map_layer_id integer,
    map_face_id integer
  ) AS $$
DECLARE
  _source integer;
  _target integer;
  _layer integer;
BEGIN
  IF _ident = 'sys\:carto-legacy' THEN
    RETURN QUERY
    SELECT
      l.line_id,
      l.source_id,
      CAST(l.geom_scale AS maps.map_scale),
      NULL::integer, NULL::integer
    FROM carto.lines l
    WHERE l.scale = map_bounds.scale_for_zoom(_zoom)
      AND ST_Intersects(l.geom, _within);
    RETURN;
  END IF;

  _source := map_bounds.resolve_source(_ident);
  _target := map_bounds.serving_source(_source, _zoom);
  IF _target IS NULL THEN
    RETURN;
  END IF;

  -- The faces are `_target`'s; without faces, its own polygons (or lines) are
  -- read.
  _layer := map_bounds.face_layer_for(_source, _zoom);

  IF _layer IS NULL THEN
    RETURN QUERY
    SELECT l.line_id, l.source_id, l.scale, NULL::integer, NULL::integer
    FROM map_bounds.lines_of(_target, _within) l;
    RETURN;
  END IF;

  RETURN QUERY
  WITH faces AS MATERIALIZED (
    SELECT mf.id AS face_id, mf.map_id AS owner_id
    FROM map_bounds_topology.map_face mf
    WHERE mf.map_layer = _layer
      AND ST_Intersects(mf.geometry, _within)
  ),
  holders AS MATERIALIZED (
    SELECT
      f.face_id,
      c.source_id AS content_id,
      c.footprint,
      cs.scale AS content_scale
    FROM faces f
    CROSS JOIN LATERAL map_bounds.content_of(f.owner_id) c
    JOIN maps.sources cs
      ON cs.source_id = c.source_id
     AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  )
  SELECT l.line_id, l.source_id, l.scale, _layer, h.face_id
  FROM holders h
  JOIN maps.lines l
    ON l.source_id = h.content_id
   AND l.scale = CAST(h.content_scale AS maps.map_scale)
   AND ST_Intersects(l.geom, _within)
  WHERE EXISTS (
      SELECT 1 FROM map_bounds_topology.map_face f
      WHERE f.id = h.face_id
        AND ST_Intersects(f.geometry, l.geom)
    )
    AND (h.footprint IS NULL OR ST_Contains(h.footprint, ST_PointOnSurface(l.geom)));
END;
$$ LANGUAGE plpgsql STABLE ROWS 50;

/* ---------------------------------------------------------------------------
   CARTO -- the served map, as one multiscale compilation.

   `carto` names the whole tree: `tiny` below zoom 3, then `carto-small`,
   `carto-medium`, `carto-large` by band. The members carry the `scale` that
   `serving_source` picks by. Its bounds open with `world`, seeded beside the
   layers' in `bounds/layers.py`. Replaces the `carto-v2` string and the
   `/dev/carto` zoom CASE.
   --------------------------------------------------------------------------- */
INSERT INTO maps.sources (slug, name, status_code, is_finalized)
VALUES ('carto', 'Carto', 'active', false)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO map_bounds.compilation (source_id, assembly_mode)
SELECT s.source_id, 'multiscale'
FROM maps.sources s
WHERE s.slug = 'carto'
ON CONFLICT (source_id) DO NOTHING;

INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
SELECT c.source_id, m.source_id, NULL
FROM maps.sources c
JOIN maps.sources m
  ON m.slug IN ('tiny', 'carto-small', 'carto-medium', 'carto-large')
WHERE c.slug = 'carto'
ON CONFLICT (compilation_id, member_id) DO NOTHING;

/** The scale each compilation of the carto tree is designated: the band a
  member of `carto` answers for, and for every one the zooms it is drawn at when
  requested by name (`zoom_range`). Only filled where unset: the `-v1`
  snapshot's already carry theirs. */
UPDATE maps.sources s
SET scale = v.scale
FROM (VALUES
  ('tiny',         'tiny'),
  ('small',        'small'),
  ('medium',       'medium'),
  ('large',        'large'),
  ('carto-small',  'small'),
  ('carto-medium', 'medium'),
  ('carto-large',  'large')
) AS v(slug, scale)
WHERE s.slug = v.slug
  AND s.scale IS NULL;

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
