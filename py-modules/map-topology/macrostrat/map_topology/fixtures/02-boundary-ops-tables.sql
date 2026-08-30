/**
  Management of boundaries for maps. This allows composing boundaries from
  multiple sources and editing them in a consistent, repeatable way.
 */

/** Vocabulary of boundary operations. A lookup table rather than an enum so
  that new operations need no migration.

  Three of them *open* a boundary, and which one is used records where the
  starting geometry came from -- so provenance is carried by the operation's
  identity rather than by a separate column:

    union   computed by us from the map''s own features
    adopt   lifted from the source dataset and promoted without recomputation
    init    supplied by hand

  All three are constrained to position 0 below.
*/
CREATE TABLE IF NOT EXISTS map_bounds.boundary_operation (
  id text PRIMARY KEY,
  description text
);
INSERT INTO map_bounds.boundary_operation (id, description)
VALUES
  ('union',            'Open the boundary with a union computed from the map''s own features. Parameters carry a working srid and a union approach. This is the implicit default when a map has no operations at all.'),
  ('adopt',            'Open the boundary with a geometry shipped by the source dataset, promoted as-is. Record which layer or file in parameters / note.'),
  ('init',             'Open the boundary with a hand-supplied geometry.'),
  ('add',              'Union an operand polygon into the boundary'),
  ('subtract',         'Difference an operand polygon out of the boundary'),
  ('buffer',           'Dilate then erode by a given distance to close small gaps'),
  ('fill_holes',       'Drop interior rings, optionally only those below a maximum area'),
  ('fix_antimeridian', 'Split, shift and re-wrap geometry spanning the antimeridian'),
  ('clip_to_world',    'Intersect with the -180/-90..180/90 envelope'),
  ('simplify',         'Douglas-Peucker simplification to a given tolerance')
ON CONFLICT (id) DO NOTHING;

/** Ordered operations composing a map's boundary.

  Chosen over a single "edited" flag, which would freeze the boundary: a frozen
  edit blocks the map from ever picking up changes to its own features.

  **Opening operations are optional.** A map with no rows at all composes as
  a `union` of its own features under default parameters. The
  system materializes an opening row only when it needs to record non-default
  parameters or cache the computed union, so absence never blocks computation and
  the common case carries no rows.
*/
CREATE TABLE IF NOT EXISTS map_bounds.boundary_op (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_id integer NOT NULL
    REFERENCES map_bounds.map_area(source_id) ON DELETE CASCADE,
  position integer NOT NULL,
  operation text NOT NULL REFERENCES map_bounds.boundary_operation(id),
  /** The starting boundary for an opening operation (for `union`, the cached
      result); the operand for add/subtract; null for parameter-only operations. */
  geometry Geometry(MultiPolygon, 4326),
  /** Operation parameters, e.g. a working srid, or a buffer distance. */
  /* `jsonb_build_object()` rather than '{...}'::jsonb: a literal brace pair is a
     positional placeholder to psycopg's SQL.format(), which fires whenever a
     pre-bind param is passed. Keeping the file brace-free defuses that. */
  parameters jsonb NOT NULL DEFAULT jsonb_build_object(),
  /** Why this correction exists -- these are editorial acts and should say so. */
  note text,
  /** Non-null if this operation failed on the last compose. */
  error text,
  /** Surrogate key, not (source_id, position): an operation's identity
      survives reordering. `position` is an attribute of an operation, not what it
      *is*, so this isn't redundant. */
  CONSTRAINT boundary_op_unique_position UNIQUE (source_id, position)
    DEFERRABLE INITIALLY IMMEDIATE,
  /** Position 0 _must_ holds an opening operation, and opening operations must appear
      nowhere else. */
  CONSTRAINT boundary_op_opening_position
    CHECK ((operation IN ('union', 'adopt', 'init')) = (position = 0))
);

