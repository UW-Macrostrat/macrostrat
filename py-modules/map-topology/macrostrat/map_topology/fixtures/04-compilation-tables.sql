/**
  COMPILATIONS

  A compilation is a map -- a `maps.sources` row assembled from other maps. It is
  not a distinct kind of thing, so there is no `map_type` column anywhere:
  "is a compilation" means *has members*, "is a constituent" means *is a member*,
  and both are read straight off `map_composition`. Whether a map holds polygons
  of its own separates a materialized compilation from a virtual one, and a
  constituent from a map that simply has not been ingested yet.
*/

CREATE TABLE IF NOT EXISTS map_bounds.map_composition (
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
  CONSTRAINT map_composition_no_self_reference
    CHECK (compilation_id != member_id)
);

CREATE INDEX IF NOT EXISTS map_composition_member_idx
  ON map_bounds.map_composition (member_id);

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
FROM map_bounds.map_composition
WHERE compilation_id = _source_id;
$$ LANGUAGE SQL STABLE;

/** Membership is traversed recursively, so a cycle does not merely give a wrong
  answer -- it fails to terminate. */
CREATE OR REPLACE FUNCTION map_bounds.check_map_composition()
  RETURNS trigger AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE ancestors AS (
      SELECT NEW.compilation_id AS id
      UNION
      SELECT mc.compilation_id
      FROM map_bounds.map_composition mc
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

CREATE OR REPLACE TRIGGER check_map_composition_trigger
  BEFORE INSERT OR UPDATE ON map_bounds.map_composition
  FOR EACH ROW EXECUTE FUNCTION map_bounds.check_map_composition();

/** FLATTENED PRIORITY

  `priority` stays authored and user-settable. `priority_path` is derived by
  `sync-priority-paths`: a map's effective standing under a root layer, built by
  concatenating the priority of every edge on the way down. Postgres compares
  arrays lexicographically, so identity resolution keeps its shape and only
  changes the column it orders by.

  `derived` marks rows the sync owns. It is needed because a base layer holds
  both kinds at once: a virtual compilation is authored into `medium`, while the
  rows for the maps it resolves to are generated.
*/
ALTER TABLE map_bounds.map_priority
  ADD COLUMN IF NOT EXISTS priority_path integer[];
ALTER TABLE map_bounds.map_priority
  ADD COLUMN IF NOT EXISTS derived boolean NOT NULL DEFAULT false;

/** Editing an authored priority drops the stale path, so resolution falls back to
  the scalar until the next sync rather than silently ignoring the edit. Same
  principle as `map_area.geometry_hash`: a derived value invalidates itself when
  the thing it was derived from moves. */
CREATE OR REPLACE FUNCTION map_bounds.invalidate_priority_path()
  RETURNS trigger AS $$
BEGIN
  IF NEW.priority IS DISTINCT FROM OLD.priority
     AND NEW.priority_path IS NOT DISTINCT FROM OLD.priority_path
  THEN
    NEW.priority_path := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER invalidate_priority_path_trigger
  BEFORE UPDATE ON map_bounds.map_priority
  FOR EACH ROW EXECUTE FUNCTION map_bounds.invalidate_priority_path();

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
FROM map_bounds.map_composition mc
JOIN maps.sources s ON s.source_id = mc.compilation_id
LEFT JOIN map_bounds.compilation c ON c.source_id = mc.compilation_id
GROUP BY mc.compilation_id, s.slug, c.assembly_mode, c.member_hash;
