ALTER TABLE storage.object DROP COLUMN IF EXISTS object_group_id;
DROP TABLE IF EXISTS storage.object_group CASCADE;

CREATE TABLE IF NOT EXISTS storage.map_files (
            id serial PRIMARY KEY,
            ingest_process_id integer NOT NULL
                REFERENCES maps_metadata.ingest_process(id) ON DELETE CASCADE,
            object_id integer NOT NULL
                REFERENCES storage.object(id) ON DELETE CASCADE
        );