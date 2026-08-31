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
  /** The member set the compilation's derived polygons were built from. NULL
    while virtual; stale once it no longer matches the current members. */
  member_hash uuid,
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

/** Compilation state: virtual, materialized, or stale. */
CREATE OR REPLACE VIEW map_bounds.compilation_sync AS
SELECT
  mc.compilation_id AS source_id,
  s.slug,
  count(*) AS n_members,
  coalesce(c.assembly_mode, 'layered') AS assembly_mode,
  map_bounds.holds_polygons(mc.compilation_id) AS materialized,
  c.member_hash,
  map_bounds.compilation_member_hash(mc.compilation_id) AS current_member_hash,
  CASE
    WHEN NOT map_bounds.holds_polygons(mc.compilation_id) THEN 'virtual'
    WHEN c.member_hash IS NOT DISTINCT FROM
         map_bounds.compilation_member_hash(mc.compilation_id) THEN 'current'
    ELSE 'stale'
  END AS state
FROM map_bounds.compilation_member mc
JOIN maps.sources s ON s.source_id = mc.compilation_id
LEFT JOIN map_bounds.compilation c ON c.source_id = mc.compilation_id
GROUP BY mc.compilation_id, s.slug, c.assembly_mode, c.member_hash;
