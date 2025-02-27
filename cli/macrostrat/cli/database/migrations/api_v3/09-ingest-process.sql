CREATE SCHEMA IF NOT EXISTS maps_metadata;

CREATE TYPE maps.ingest_state AS ENUM (
  'pending',
  'ingested',
  'prepared',
  'failed',
  'abandoned',
  'post_harmonization'
);

CREATE TYPE maps.ingest_type AS ENUM (
  'vector',
  'ta1_output'
);

CREATE TABLE maps_metadata.ingest_process
(
    id                serial primary key,
    state             maps.ingest_state,
    type              maps.ingest_type,
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


CREATE TABLE maps_metadata.ingest_process_tag (
    ingest_process_id integer NOT NULL
        references maps_metadata.ingest_process,
    tag character varying(255) NOT NULL
);
