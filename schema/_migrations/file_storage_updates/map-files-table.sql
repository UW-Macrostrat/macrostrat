ALTER TABLE storage.objects DROP COLUMN IF EXISTS object_group_id;
DROP TABLE IF EXISTS storage.object_group CASCADE;
CREATE TABLE IF NOT EXISTS maps_metadata.map_files (
            id serial PRIMARY KEY,
            ingest_process_id integer NOT NULL
                REFERENCES maps_metadata.ingest_process(id) ON DELETE CASCADE,
            object_id integer NOT NULL
                REFERENCES storage.object(id) ON DELETE CASCADE
        );
ALTER TABLE maps_metadata.map_files
ADD CONSTRAINT unique_ingest_object
UNIQUE (ingest_process_id, object_id);
