--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: ingest_process; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS ingest_process (
    id SERIAL,
    state maps.ingest_state,
    comments text,
    source_id integer,
    created_on timestamptz DEFAULT now() NOT NULL,
    completed_on timestamptz,
    map_id text,
    type maps.ingest_type,
    polygon_state jsonb,
    line_state jsonb,
    point_state jsonb,
    ingest_pipeline text,
    map_url text,
    ingested_by text,
    slug text,
    CONSTRAINT ingest_process_pkey PRIMARY KEY (id)
);

--
-- Name: ingest_process_tag; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS ingest_process_tag (
    ingest_process_id integer,
    tag varchar(255),
    CONSTRAINT pk_tag PRIMARY KEY (ingest_process_id, tag),
    CONSTRAINT ingest_process_tag_ingest_process_id_fkey FOREIGN KEY (ingest_process_id) REFERENCES ingest_process (id)
);

--
-- Name: map_files; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS map_files (
    id integer GENERATED ALWAYS AS IDENTITY,
    ingest_process_id integer NOT NULL,
    object_id integer NOT NULL,
    CONSTRAINT map_files_pkey PRIMARY KEY (id),
    CONSTRAINT map_files_ingest_process_id_object_id_key UNIQUE (ingest_process_id, object_id),
    CONSTRAINT map_files_ingest_process_id_fkey FOREIGN KEY (ingest_process_id) REFERENCES ingest_process (id) ON DELETE CASCADE
);

--
-- Name: sources; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS sources (
    source_id integer,
    raster_bucket_url text,
    date_compiled timestamp,
    compiler_name text,
    raster_source_url text
);

--
-- Name: sources_metadata; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS sources_metadata (
    source_id integer,
    raster_bucket_url text,
    date_compiled timestamp,
    compiler_name text,
    raster_source_url text,
    name varchar(255),
    url varchar(255),
    ref_title text,
    authors varchar(255),
    ref_year text,
    ref_source varchar(255),
    isbn_doi varchar(100),
    scale varchar(20),
    licence varchar(100),
    features integer,
    area integer,
    priority boolean,
    display_scales text[],
    status_code text,
    slug text
);

--
-- Name: ingest_process_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE ingest_process
ADD CONSTRAINT ingest_process_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: map_files_object_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE map_files
ADD CONSTRAINT map_files_object_id_fkey FOREIGN KEY (object_id) REFERENCES storage.object (id);

--
-- Name: maps_metadata_update_trigger(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION maps_metadata_update_trigger()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
	UPDATE
		maps_metadata.sources
	SET
		raster_source_url = NEW.raster_source_url,
		raster_bucket_url = NEW.raster_bucket_url,
		compiler_name = NEW.compiler_name,
		date_compiled = NEW.date_compiled
	WHERE source_id = NEW.source_id;
	RETURN NEW;
END;
$$;

--
-- Name: sources_meta; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW sources_meta AS
 SELECT ms.source_id,
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
    s.license AS licence,
    s.features,
    s.area,
    s.priority,
    s.display_scales,
    s.status_code,
    s.slug
   FROM maps.sources s
     LEFT JOIN sources ms ON ms.source_id = s.source_id;

