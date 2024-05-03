CREATE TABLE maps_metadata.ingest_process_tag (
    ingest_process_id integer NOT NULL,
    tag character varying(255) NOT NULL
);


ALTER TABLE maps_metadata.ingest_process_tag OWNER TO macrostrat;
