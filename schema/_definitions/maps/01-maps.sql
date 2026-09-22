
CREATE SCHEMA maps;


/** Which of a legend entry's text fields a stratigraphic name was found in.

  Evidence, not bookkeeping. A name in `strat_name` or `name` *is* this unit; a
  name in `descrip` is a *mention*, and descriptions name correlative, overlying
  and bounding units as readily as their own. Declared in strength order, so
  `min(match_field)` is the strongest evidence for a match.
*/
CREATE TYPE maps.strat_name_match_field AS ENUM (
    'strat_name',
    'name',
    'descrip',
    'comments'
);

CREATE TYPE maps.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);

CREATE FUNCTION maps.lines_geom_is_valid(geom public.geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_LineString', 'ST_MultiLineString');
$$;

CREATE FUNCTION maps.polygons_geom_is_valid(geom public.geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
$$;
/** Which slice of the geologic record a map depicts.

  An open lookup rather than an enum on purpose: the four values below are NGS's
  seed vocabulary, and a geolayer is really any set of elements that mosaic in
  time -- eventually a temporal selection predicate rather than four buckets. New
  values must not need a migration.

  NULL means unspecified, and is read as `surface`: every map Macrostrat served
  before this column existed is a surface map, so the default preserves their
  behaviour without asserting anything about them.
*/
CREATE TABLE maps.geolayer (
  id          text PRIMARY KEY,
  description text NOT NULL
);

INSERT INTO maps.geolayer (id, description) VALUES
  ('surface', 'What is present at Earth''s surface.'),
  ('quaternary',
   'Quaternary geology, in many cases inclusive of units spanning the beginning '
   'of the Quaternary.'),
  ('pre-quaternary',
   'Geology older than the Quaternary, including geology beneath Quaternary '
   'deposits.'),
  ('precambrian',
   'Precambrian geology, typically where it is buried beneath younger cover.')
ON CONFLICT (id) DO NOTHING;

SET default_tablespace = '';

CREATE TABLE maps.sources (
  source_id serial PRIMARY KEY,
  name character varying(255),
  primary_table character varying(255),
  url character varying(255),
  ref_title text,
  authors character varying(255),
  ref_year text,
  ref_source character varying(255),
  ref_compilation text,
  isbn_doi character varying(100),
  scale character varying(20),
  primary_line_table character varying(50),
  license character varying(100),
  features integer,
  area integer,
  priority boolean DEFAULT false,
  rgeom public.geometry,
  display_scales text[],
  web_geom public.geometry,
  new_priority integer DEFAULT 0,
  status_code text DEFAULT 'active'::text,
  slug text NOT NULL UNIQUE,
  raster_url text,
  scale_denominator integer,
  is_finalized boolean DEFAULT false,
  lines_oriented boolean,
  date_finalized timestamp with time zone,
  ingested_by text,
  keywords text[],
  language text,
  description character varying,
  superseded_by integer REFERENCES maps.sources(source_id),
  geolayer text REFERENCES maps.geolayer(id),
  CONSTRAINT sources_not_self_superseding CHECK (superseded_by <> source_id)
);

CREATE INDEX sources_superseded_by_idx ON maps.sources USING btree (superseded_by);

COMMENT ON COLUMN maps.sources.slug IS 'Unique identifier for each Macrostrat source';

COMMENT ON COLUMN maps.sources.geolayer IS
  'Which slice of the geologic record this map depicts. NULL means unspecified '
  'and is read as `surface`. Load-bearing for assembly: the scale layers '
  '(`tiny`/`small`/`medium`/`large`) are *surface* layers, so a map depicting '
  'something else -- Precambrian basement, Quaternary cover -- is a real map '
  'with a real boundary that has no place in a surface stack. Checked when '
  'membership is authored -- `macrostrat compilations add` refuses it, '
  '`compilations lint` reports one that went stale -- rather than enforced on '
  'sync: layer membership is curated, and withdrawing a map from a layer is a '
  'decision somebody makes, not one a sweep makes behind them.';

COMMENT ON COLUMN maps.sources.superseded_by IS
  'The map that replaces this one, where a better product covers the same '
  'ground -- SGMC by NGS, our Alaska compilation by NGS''s. `WHERE '
  'superseded_by IS NULL` is the set of maps that should still be used. '
  'Functional by nature (a map has at most one successor), which is why it is a '
  'column rather than a relation table; where no single map replaces an old one '
  'the successor is a compilation, which is a map. Distinct from status_code: a '
  'superseded map is not obsolete, it remains a real unit of work, citable and '
  'browsable, and only stops contributing to assembly. Advisory, not enforced: '
  'it is checked where membership is authored, and an existing edge stands until '
  'somebody withdraws it.';

COMMENT ON COLUMN maps.sources.ref_compilation IS
  'Published compilation or programme this map was produced under -- NGS, SGMC, '
  'IODP. Bibliographic, like the other ref_ fields, and distinct from '
  'map_bounds.compilation_member, which records what a map is assembled from. '
  'Free text and single-valued on purpose: a placeholder until organizations and '
  'projects are modelled properly, kept deliberately too small to grow into them.';

-- TODO: integrate lines sequence into maps schema
CREATE TABLE maps.lines (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale NOT NULL,
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
)
PARTITION BY LIST (scale);
SET default_table_access_method = heap;

/** TODO: make this sequence a bit more generic */
CREATE SEQUENCE maps.legend_legend_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;

CREATE TABLE maps.legend (
    legend_id integer DEFAULT nextval('maps.legend_legend_id_seq'::regclass) PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id),
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    b_interval integer,
    t_interval integer,
    best_age_bottom numeric,
    best_age_top numeric,
    color text,
    unit_ids integer[],
    concept_ids integer[],
    strat_name_ids integer[],
    strat_name_children integer[],
    lith_ids integer[],
    lith_types text[],
    lith_classes text[],
    all_lith_ids integer[],
    all_lith_types text[],
    all_lith_classes text[],
    area numeric,
    tiny_area numeric,
    small_area numeric,
    medium_area numeric,
    large_area numeric
);

-- Not sure if this is necessary, but it seems like a good idea to link the sequence to the table column
ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;

CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);

CREATE SEQUENCE maps.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE maps.polygons (
    map_id integer DEFAULT nextval('maps.map_ids'::regclass) NOT NULL,
    source_id integer NOT NULL,
    scale maps.map_scale NOT NULL,
    orig_id text,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    PRIMARY KEY (map_id, scale) -- can't declare a unique constraint across partitions.
)
PARTITION BY LIST (scale);

GRANT USAGE ON SCHEMA maps TO web_admin;
GRANT SELECT ON TABLE maps.sources TO web_admin;

CREATE TABLE maps.points (
    source_id integer NOT NULL,
    strike integer,
    dip integer,
    dip_dir integer,
    point_type character varying(100),
    certainty character varying(100),
    comments text,
    geom public.geometry(Geometry,4326),
    point_id integer NOT NULL,
    orig_id text,
    CONSTRAINT dip_lt_90 CHECK ((dip <= 90)),
    CONSTRAINT dip_positive CHECK ((dip >= 0)),
    CONSTRAINT direction_lt_360 CHECK ((dip_dir <= 360)),
    CONSTRAINT direction_positive CHECK ((dip_dir >= 0)),
    CONSTRAINT enforce_point_geom CHECK (public.st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK ((strike <= 360)),
    CONSTRAINT strike_positive CHECK ((strike >= 0))
);

CREATE TABLE maps.polygons_large (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'large'::maps.map_scale NOT NULL,
    CONSTRAINT enforce_valid_geom_large CHECK (public.st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_large_scale_check CHECK ((scale = 'large'::maps.map_scale)),
    CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id),
    PRIMARY KEY (map_id, scale) -- can't declare a unique constraint across partitions.
);

CREATE TABLE maps.lines_large (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'large'::maps.map_scale NOT NULL,
    CONSTRAINT lines_large_scale_check CHECK ((scale = 'large'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

CREATE TABLE maps.lines_medium (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'medium'::maps.map_scale NOT NULL,
    CONSTRAINT lines_medium_scale_check CHECK ((scale = 'medium'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

CREATE TABLE maps.lines_small (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'small'::maps.map_scale NOT NULL,
    CONSTRAINT lines_small_scale_check CHECK ((scale = 'small'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

CREATE TABLE maps.lines_tiny (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'tiny'::maps.map_scale NOT NULL,
    CONSTRAINT isvalid CHECK (public.st_isvalid(geom)),
    CONSTRAINT lines_tiny_scale_check CHECK ((scale = 'tiny'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

/** Hand-made additions and removals layered over the derived strat-name and unit
  matches for a polygon.

  `map_id` deliberately carries **no** foreign key: `maps.polygons` is partitioned
  by scale, so its primary key is `(map_id, scale)` and a unique index on `map_id`
  alone cannot exist. The reference is unenforceable rather than unenforced.

  That matters because `maps.polygons.map_id` defaults to `nextval('maps.map_ids')`
  and is therefore regenerated when a source is re-ingested -- so curation for that
  source silently stops resolving, with nothing to notice. The durable key is
  `(source_id, orig_id)`, which is what re-ingestion preserves; rekeying to it is
  the real repair, and is tracked separately.
*/
CREATE TABLE maps.manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20),
    CONSTRAINT manual_matches_pkey PRIMARY KEY (match_id),
    CONSTRAINT manual_matches_unit_fk FOREIGN KEY (unit_id)
      REFERENCES macrostrat.units(id),
    -- 53 of 21,711 rows point at strat names that no longer exist. `NOT VALID`
    -- stops new ones without asserting the past is clean, the way
    -- `strat_tree_refs_fk` already does.
    CONSTRAINT manual_matches_strat_name_fk FOREIGN KEY (strat_name_id)
      REFERENCES macrostrat.strat_names(id) NOT VALID
);

CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;

CREATE TABLE maps.map_legend (
  -- no cascade delete on legend_id link prevents orphaned polygons if a legend entry is deleted
  legend_id integer NOT NULL REFERENCES maps.legend(legend_id),
  -- we allow polygons to be deleted without restriction, removing downstream map_legend entries
  map_id integer NOT NULL, -- Can't create a foreign key to maps.polygons(id) because it's partitioned.
    -- Would also need to mention scale. Perhaps we should revisit this (either partitioning or foreign key) in the future.
  UNIQUE (legend_id, map_id) -- not null, unique constraints ~ primary key
);

CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);
CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);

CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);

/** Stratigraphic names matched to map legend entries.

  The grain is the legend entry, because that is where the judgment is made: one
  row per (legend entry, name, field the name was found in). The polygon fan-out
  is derived through `maps.map_legend` into `maps.map_strat_names`, not stored
  twice over.

  It replaces a single `basis_col varchar(50)` that packed four independent facts
  into one string -- the text field, which pair of pre-normalized columns was
  compared, whether space was buffered, whether time was fuzzed -- and could
  record neither when a match was made nor whether the rank agreed.
*/
CREATE TABLE maps.legend_strat_names (
    legend_id integer NOT NULL
        REFERENCES maps.legend (legend_id) ON DELETE CASCADE,
    strat_name_id integer NOT NULL,
    match_field maps.strat_name_match_field NOT NULL,
    /** Did the rank the map's text asserted agree with the lexicon's?

      Recorded, never enforced. `macrostrat.strat_names.rank` has no `Suite`, so
      "New Hampshire Plutonic Suite" is stored as `Gp` while its own name says
      Suite, and a map may legitimately call a Macrostrat group a formation.
      Rejecting those cost 110 true matches on SGMC. NULL where the text asserted
      no rank. */
    rank_agrees boolean,
    /** Spatial corroboration, independent of the name. False means the match was
      admitted on a buffered footprint; NULL means the lexicon holds no footprint
      for the name, which is true of 2,693 of 51,229 entries and is not evidence
      against it. */
    in_footprint boolean,
    /** Temporal corroboration. NULL where the legend entry carries no interval
      to compare against. */
    age_overlaps boolean,
    /** A human asserted this, and no matcher may withdraw it. Today this is
      `basis_col LIKE 'manual%'`, which is why every delete in the pipeline
      carries that predicate as a string test. */
    is_manual boolean NOT NULL DEFAULT false,
    /** Matching is re-run as the lexicon and the descriptions change, and
      `basis_col` recorded how a match was made but never when. */
    matched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (legend_id, strat_name_id, match_field)
);

CREATE INDEX legend_strat_names_strat_name_id_idx
    ON maps.legend_strat_names USING btree (strat_name_id);

/* Read on every re-match, to be carried across it. */
CREATE INDEX legend_strat_names_manual_idx
    ON maps.legend_strat_names USING btree (legend_id) WHERE is_manual;

/** The rows `maps.map_strat_names` held before it became a view.

  Transitional, and meant to be dropped. Twelve additive match passes wrote
  22,304,055 rows expressing 64,897 distinct facts, and all of it is matcher
  output that re-running a matcher reproduces -- except the 152 human-asserted
  matches, which the `legend-strat-names` migration carries across. It is kept
  only so the old answer can be diffed against the new one.

  Declared here rather than left undeclared so it does not surface as a pending
  drop in every schema plan. Deleting this declaration is how it eventually goes
  away, once a re-match has been compared against it.
*/
CREATE TABLE maps.map_strat_names_backup (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);

/** Polygon-grain view of `maps.legend_strat_names`.

  The matching decision is made once per legend entry; this is where the polygons
  that share that entry get their copy of it, through `maps.map_legend`. It was a
  table, holding every copy: 22.3M rows for 64,897 facts.

  It stays under its old name, with its old columns, because the v2 API reads it
  --  `macrostrat-api/v2/geologic_units_burwell_nearby.ts` joins it on `map_id`,
  and ignores `basis_col` entirely -- and because `maps.map_units` matching scans
  it per source. Everything else in v2 reads the arrays built downstream of it
  (`maps.legend.strat_name_ids`, `public.lookup_<scale>.strat_name_ids`,
  `strat_name_children`, `concept_ids`), which are untouched: the two precedence
  ladders that build them keep reading this name.

  `basis_col` is therefore synthesized rather than stored. The mapping is exact
  for three of the four things the string used to pack:

      field   -> match_field
      _fspace -> NOT in_footprint      (admitted on a buffered footprint)
      _ftime  -> NOT age_overlaps      (admitted on age fuzz)
      _ntime  -> age_overlaps IS NULL  (no interval to compare)

  `_fname` is never emitted. It meant "the fuzzy one of two differently
  pre-normalized column pairs was compared", and both sides are now normalized by
  the same function, so the distinction has no analogue. That loses nothing: both
  ladders already rank every non-`_fname` tier *above* the `_fname` family, so
  matches land at the stronger tiers without either ladder changing.
*/
CREATE VIEW maps.map_strat_names AS
SELECT
    ml.map_id,
    lsn.strat_name_id,
    (CASE
        WHEN lsn.is_manual THEN 'manual'
        ELSE lsn.match_field::text
            || CASE WHEN lsn.in_footprint IS FALSE THEN '_fspace' ELSE '' END
            || CASE
                   WHEN lsn.age_overlaps IS NULL THEN '_ntime'
                   WHEN lsn.age_overlaps IS FALSE THEN '_ftime'
                   ELSE ''
               END
    END)::character varying(50) AS basis_col
FROM maps.legend_strat_names lsn
JOIN maps.map_legend ml ON ml.legend_id = lsn.legend_id;

CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);

CREATE TABLE maps.polygons_medium (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'medium'::maps.map_scale NOT NULL,
    CONSTRAINT enforce_valid_geom_medium CHECK (public.st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_medium_scale_check CHECK ((scale = 'medium'::maps.map_scale)),
    CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id),
    PRIMARY KEY (map_id, scale) -- can't declare a unique constraint across partitions.
);

CREATE SEQUENCE maps.points_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE maps.points_point_id_seq OWNED BY maps.points.point_id;

CREATE TABLE maps.polygons_small (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'small'::maps.map_scale NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_small_scale_check CHECK ((scale = 'small'::maps.map_scale)),
    CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id),
    PRIMARY KEY (map_id, scale) -- can't declare a unique constraint across partitions.
);

CREATE TABLE maps.polygons_tiny (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'tiny'::maps.map_scale NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_tiny_scale_check CHECK ((scale = 'tiny'::maps.map_scale)),
    CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id),
    PRIMARY KEY (map_id, scale) -- can't declare a unique constraint across partitions.
);

CREATE TABLE maps.source_operations (
    id integer NOT NULL,
    source_id integer NOT NULL,
    user_id integer,
    operation text NOT NULL,
    app text NOT NULL,
    comments text,
    details jsonb,
    date timestamp with time zone DEFAULT now() NOT NULL
);

create table maps.line_type (
    id text not null primary key,
    description text
);

create table maps.point_type (
    id text not null primary key,
    description text
);

COMMENT ON TABLE maps.source_operations IS 'Tracks management operations for Macrostrat maps';

CREATE SEQUENCE maps.source_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE maps.source_operations_id_seq OWNED BY maps.source_operations.id;

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_large FOR VALUES IN ('large');

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_medium FOR VALUES IN ('medium');

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_small FOR VALUES IN ('small');

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_tiny FOR VALUES IN ('tiny');

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_large FOR VALUES IN ('large');

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_medium FOR VALUES IN ('medium');

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_small FOR VALUES IN ('small');

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_tiny FOR VALUES IN ('tiny');

ALTER TABLE ONLY maps.manual_matches ALTER COLUMN match_id SET DEFAULT nextval('maps.manual_matches_match_id_seq'::regclass);

ALTER TABLE ONLY maps.points ALTER COLUMN point_id SET DEFAULT nextval('maps.points_point_id_seq'::regclass);

ALTER TABLE ONLY maps.source_operations ALTER COLUMN id SET DEFAULT nextval('maps.source_operations_id_seq'::regclass);

ALTER TABLE ONLY maps.legend_liths
    ADD CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col);

ALTER TABLE ONLY maps.lines
    ADD CONSTRAINT lines_pkey PRIMARY KEY (line_id, scale);

ALTER TABLE ONLY maps.lines_large
    ADD CONSTRAINT lines_large_pkey PRIMARY KEY (line_id, scale);

ALTER TABLE ONLY maps.lines_medium
    ADD CONSTRAINT lines_medium_pkey PRIMARY KEY (line_id, scale);

ALTER TABLE ONLY maps.lines_small
    ADD CONSTRAINT lines_small_pkey PRIMARY KEY (line_id, scale);

ALTER TABLE ONLY maps.lines_tiny
    ADD CONSTRAINT lines_tiny_pkey PRIMARY KEY (line_id, scale);

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT map_sources_name_key UNIQUE (primary_table);

ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_pkey PRIMARY KEY (id);

CREATE INDEX polygons_b_interval_idx ON ONLY maps.polygons USING btree (b_interval);

CREATE INDEX large_b_interval_idx ON maps.polygons_large USING btree (b_interval);

CREATE INDEX polygons_geom_idx ON ONLY maps.polygons USING gist (geom);

CREATE INDEX large_geom_idx ON maps.polygons_large USING gist (geom);

CREATE INDEX polygons_name_idx ON ONLY maps.polygons USING btree (name);

CREATE INDEX large_name_idx ON maps.polygons_large USING btree (name);

CREATE INDEX polygons_orig_id_idx ON ONLY maps.polygons USING btree (orig_id);

CREATE INDEX large_orig_id_idx ON maps.polygons_large USING btree (orig_id);

CREATE INDEX polygons_source_id_idx ON ONLY maps.polygons USING btree (source_id);

CREATE INDEX large_source_id_idx ON maps.polygons_large USING btree (source_id);

CREATE INDEX polygons_t_interval_idx ON ONLY maps.polygons USING btree (t_interval);

CREATE INDEX large_t_interval_idx ON maps.polygons_large USING btree (t_interval);

CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);

CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);

CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);

CREATE INDEX lines_geom_idx ON ONLY maps.lines USING gist (geom);

CREATE INDEX lines_large_geom_idx ON maps.lines_large USING gist (geom);

CREATE INDEX lines_line_id_idx ON ONLY maps.lines USING btree (line_id);

CREATE INDEX lines_large_line_id_idx ON maps.lines_large USING btree (line_id);

CREATE INDEX lines_orig_id_idx ON ONLY maps.lines USING btree (orig_id);

CREATE INDEX lines_large_orig_id_idx ON maps.lines_large USING btree (orig_id);

CREATE INDEX lines_source_id_idx ON ONLY maps.lines USING btree (source_id);

CREATE INDEX lines_large_source_id_idx ON maps.lines_large USING btree (source_id);

CREATE INDEX lines_medium_geom_idx ON maps.lines_medium USING gist (geom);

CREATE INDEX lines_medium_line_id_idx ON maps.lines_medium USING btree (line_id);

CREATE INDEX lines_medium_orig_id_idx ON maps.lines_medium USING btree (orig_id);

CREATE INDEX lines_medium_source_id_idx ON maps.lines_medium USING btree (source_id);

CREATE INDEX lines_small_geom_idx ON maps.lines_small USING gist (geom);

CREATE INDEX lines_small_line_id_idx ON maps.lines_small USING btree (line_id);

CREATE INDEX lines_small_orig_id_idx ON maps.lines_small USING btree (orig_id);

CREATE INDEX lines_small_source_id_idx ON maps.lines_small USING btree (source_id);

CREATE INDEX lines_tiny_geom_idx ON maps.lines_tiny USING gist (geom);

CREATE INDEX lines_tiny_line_id_idx ON maps.lines_tiny USING btree (line_id);

CREATE INDEX lines_tiny_orig_id_idx ON maps.lines_tiny USING btree (orig_id);

CREATE INDEX lines_tiny_source_id_idx ON maps.lines_tiny USING btree (source_id);

CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);

CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);

CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);

CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);

CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);

CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);

CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);

CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);

CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);

CREATE INDEX medium_b_interval_idx ON maps.polygons_medium USING btree (b_interval);

CREATE INDEX medium_geom_idx ON maps.polygons_medium USING gist (geom);

CREATE INDEX medium_orig_id_idx ON maps.polygons_medium USING btree (orig_id);

CREATE INDEX medium_source_id_idx ON maps.polygons_medium USING btree (source_id);

CREATE INDEX medium_t_interval_idx ON maps.polygons_medium USING btree (t_interval);

CREATE INDEX points_geom_idx ON maps.points USING gist (geom);

CREATE INDEX points_source_id_idx ON maps.points USING btree (source_id);

CREATE INDEX polygons_medium_name_idx ON maps.polygons_medium USING btree (name);

CREATE INDEX polygons_small_name_idx ON maps.polygons_small USING btree (name);

CREATE INDEX polygons_tiny_name_idx ON maps.polygons_tiny USING btree (name);

CREATE INDEX small_b_interval_idx ON maps.polygons_small USING btree (b_interval);

CREATE INDEX small_geom_idx ON maps.polygons_small USING gist (geom);

CREATE INDEX small_orig_id_idx ON maps.polygons_small USING btree (orig_id);

CREATE INDEX small_source_id_idx ON maps.polygons_small USING btree (source_id);

CREATE INDEX small_t_interval_idx ON maps.polygons_small USING btree (t_interval);

CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);

CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);

CREATE INDEX tiny_b_interval_idx ON maps.polygons_tiny USING btree (b_interval);

CREATE INDEX tiny_geom_idx ON maps.polygons_tiny USING gist (geom);

CREATE INDEX tiny_orig_id_idx ON maps.polygons_tiny USING btree (orig_id);

CREATE INDEX tiny_source_id_idx ON maps.polygons_tiny USING btree (source_id);

CREATE INDEX tiny_t_interval_idx ON maps.polygons_tiny USING btree (t_interval);

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.large_b_interval_idx;

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.large_geom_idx;

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.large_name_idx;

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.large_orig_id_idx;

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.large_source_id_idx;

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.large_t_interval_idx;

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_large_geom_idx;

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_large_line_id_idx;

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_large_orig_id_idx;

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_large_pkey;

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_large_source_id_idx;

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_medium_geom_idx;

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_medium_line_id_idx;

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_medium_orig_id_idx;

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_medium_pkey;

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_medium_source_id_idx;

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_small_geom_idx;

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_small_line_id_idx;

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_small_orig_id_idx;

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_small_pkey;

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_small_source_id_idx;

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_tiny_geom_idx;

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_tiny_line_id_idx;

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_tiny_orig_id_idx;

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_tiny_pkey;

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_tiny_source_id_idx;

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_large_pkey;

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_medium_pkey;

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_small_pkey;

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_tiny_pkey;

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.medium_b_interval_idx;

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.medium_geom_idx;

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.medium_orig_id_idx;

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.medium_source_id_idx;

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.medium_t_interval_idx;

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_medium_name_idx;

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_small_name_idx;

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_tiny_name_idx;

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.small_b_interval_idx;

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.small_geom_idx;

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.small_orig_id_idx;

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.small_source_id_idx;

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.small_t_interval_idx;

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.tiny_b_interval_idx;

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.tiny_geom_idx;

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.tiny_orig_id_idx;

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.tiny_source_id_idx;

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.tiny_t_interval_idx;

ALTER TABLE maps.lines
    ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

ALTER TABLE ONLY maps.points
    ADD CONSTRAINT points_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

ALTER TABLE maps.polygons
    ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id) ON DELETE CASCADE;

ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE SET NULL;






