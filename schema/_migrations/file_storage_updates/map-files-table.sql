CREATE TABLE IF NOT EXISTS maps_metadata.map_files (
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ingest_process_id integer NOT NULL
      REFERENCES maps_metadata.ingest_process(id) ON DELETE CASCADE,
  object_id integer NOT NULL REFERENCES storage.object(id),
  -- No cascade: don't allow deletion of files in use without explicit dereferencing
  UNIQUE (ingest_process_id, object_id) -- prevent duplicate entries for the same file in one ingest
);
