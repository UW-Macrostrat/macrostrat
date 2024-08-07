CREATE SCHEMA IF NOT EXISTS maps_metadata;

CREATE TYPE ingest_state AS ENUM ('pending', 'ingested', 'prepared', 'failed', 'abandoned', 'post_harmonization');
CREATE TYPE ingest_type AS ENUM ('vector', 'ta1_output');

CREATE TABLE maps_metadata.ingest_process
(
    id                serial primary key,
    state             ingest_state,
    type              ingest_type,
    comments          text,
    source_id         integer
        references maps.sources,
    access_group_id   integer
        references macrostrat_auth."group",
    object_group_id   integer not null
        references storage.object_group,
    created_on        timestamp with time zone default now() not null,
    completed_on      timestamp with time zone,
    map_id            text
);

ALTER TABLE maps_metadata.ingest_process
    owner to macrostrat;

CREATE TABLE maps_metadata.ingest_process_tag (
    ingest_process_id integer NOT NULL
        references maps_metadata.ingest_process,
    tag character varying(255) NOT NULL
);

ALTER TABLE maps_metadata.ingest_process_tag OWNER TO macrostrat;
