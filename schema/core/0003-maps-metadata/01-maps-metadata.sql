/** Schema for the map ingestion system */

CREATE SCHEMA maps_metadata;
CREATE SCHEMA IF NOT EXISTS sources;


CREATE TABLE maps_metadata.ingest_state (
  id               text not null primary key,
  description      text,
  color            varchar(25)
);

/** Is there a difference between ingest_state and tags? */

INSERT INTO maps_metadata.ingest_state (id)
VALUES ('pending'),
  ('ingested'),
  ('prepared'),
  ('failed'),
  ('abandoned'),
  ('post_harmonization'),
  ('pre-processed'),
  ('post-processed'),
  ('needs review'),
  ('finalized'),
  ('ready')
ON CONFLICT (id) DO NOTHING;


/** Ingestion results for pipeline steps */
CREATE TABLE maps_metadata.ingest_result (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY ,
  source_id integer NOT NULL REFERENCES maps.sources(source_id),
  description text,
  error text,
  processing_step text,
  date timestamp with time zone DEFAULT now() NOT NULL,
  details jsonb -- random information for debugging (e.g., which strat names didn't match)
);


CREATE TABLE maps_metadata.ingest_process (
    -- This id is deprecated in favor of just using the source_id as the primary key,
    -- which we will converge on eventually.
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    state text references maps_metadata.ingest_state (id),
    comments text,
    source_id integer not null
        constraint ingest_process_source_id_unique unique
        references maps.sources(source_id),
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    completed_on timestamp with time zone,
    -- These are for UI / table state (omitted columns, column order, etc.)
    polygon_state jsonb,
    line_state jsonb,
    point_state jsonb,
    -- Which pipeline was used to ingest
    ingest_pipeline text,
    ingested_by text,
    -- Redundant but useful for debugging
    slug text references maps.sources (slug)
);


CREATE TABLE maps_metadata.ingest_process_tag (
    ingest_process_id integer NOT NULL,
    tag character varying(255) NOT NULL
);


CREATE TABLE maps_metadata.map_files (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingest_process_id integer NOT NULL,
    object_id integer NOT NULL
);

CREATE TABLE maps_metadata.sources (
    source_id integer,
    raster_bucket_url text,
    date_compiled timestamp without time zone,
    compiler_name text,
    raster_source_url text
);

CREATE VIEW maps_metadata.sources_meta AS
SELECT
  ms.source_id,
  ms.raster_bucket_url,
  ms.date_compiled,
  ms.compiler_name,
  ms.raster_source_url,
  s.name,
  s.url,
  s.ref_title,
  s.authors,
  s.ref_year,
  s.ref_source,
  s.isbn_doi,
  s.scale,
  s.license,
  s.features,
  s.area,
  s.priority,
  s.display_scales,
  s.status_code,
  s.slug
FROM maps.sources s
LEFT JOIN maps_metadata.sources ms
  ON ms.source_id = s.source_id
LEFT JOIN maps_metadata.ingest_process ip
  ON ip.source_id = s.source_id;

/** Sources meta table, inherits from sources table and can be updated via a trigger */
CREATE OR REPLACE FUNCTION maps_metadata.maps_metadata_update_trigger() RETURNS trigger
  LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE
    sources
  SET
    raster_source_url = NEW.raster_source_url,
    raster_bucket_url = NEW.raster_bucket_url,
    compiler_name = NEW.compiler_name,
    date_compiled = NEW.date_compiled
  WHERE source_id = NEW.source_id;
  RETURN NEW;
END;
$$;

CREATE TRIGGER maps_metadata_update_trigger
  INSTEAD OF UPDATE ON maps_metadata.sources_meta
  FOR EACH ROW EXECUTE FUNCTION maps_metadata.maps_metadata_update_trigger();

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_ingest_process_id_object_id_key UNIQUE (ingest_process_id, object_id);

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_pkey PRIMARY KEY (id);

ALTER TABLE ONLY maps_metadata.ingest_process_tag
    ADD CONSTRAINT pk_tag PRIMARY KEY (ingest_process_id, tag);


ALTER TABLE ONLY maps_metadata.ingest_process
    ADD CONSTRAINT ingest_process_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

ALTER TABLE ONLY maps_metadata.ingest_process_tag
    ADD CONSTRAINT ingest_process_tag_ingest_process_id_fkey FOREIGN KEY (ingest_process_id) REFERENCES maps_metadata.ingest_process(id);

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_ingest_process_id_fkey FOREIGN KEY (ingest_process_id) REFERENCES maps_metadata.ingest_process(id) ON DELETE CASCADE;

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_object_id_fkey FOREIGN KEY (object_id) REFERENCES storage.object(id);

GRANT SELECT,UPDATE ON TABLE maps_metadata.ingest_process TO web_user;

GRANT USAGE ON SCHEMA maps_metadata TO web_admin;
