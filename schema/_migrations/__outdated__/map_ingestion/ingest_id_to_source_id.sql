-- 1. Drop dependent views. `map_ingest_metadata` is retired for good (identical
--    to `map_ingest`); the rest are recreated in step 6.
DROP VIEW IF EXISTS map_ingestion_api.maps;
DROP VIEW IF EXISTS macrostrat_api.map_ingest_tags;
DROP VIEW IF EXISTS macrostrat_api.map_ingest;
DROP VIEW IF EXISTS macrostrat_api.map_ingest_metadata;

-- 2. Drop the child FKs pointing at ingest_process(id).
ALTER TABLE maps_metadata.ingest_process_tag
  DROP CONSTRAINT IF EXISTS ingest_process_tag_ingest_process_id_fkey;
ALTER TABLE maps_metadata.map_files
  DROP CONSTRAINT IF EXISTS map_files_ingest_process_id_fkey;

-- 3. Retire the id-sync trigger from the earlier data script (now obsolete).
DROP TRIGGER IF EXISTS sync_ingest_process_id_with_source_id_trigger
  ON maps_metadata.ingest_process;
DROP FUNCTION IF EXISTS maps_metadata.sync_ingest_process_id_with_source_id();

-- 4. Backfill the children FIRST, while ingest_process.id still exists, so the
--    mapping comes from the actual row and not an id = source_id assumption.
ALTER TABLE maps_metadata.ingest_process_tag ADD COLUMN source_id integer;
UPDATE maps_metadata.ingest_process_tag t
  SET source_id = ip.source_id
  FROM maps_metadata.ingest_process ip
  WHERE t.ingest_process_id = ip.id;
select * from maps_metadata.ingest_process_tag where source_id is null;
DELETE FROM maps_metadata.ingest_process_tag WHERE source_id IS NULL;
ALTER TABLE maps_metadata.ingest_process_tag ALTER COLUMN source_id SET NOT NULL;
select * from maps_metadata.ingest_process_tag

ALTER TABLE maps_metadata.map_files ADD COLUMN source_id integer;
UPDATE maps_metadata.map_files f
  SET source_id = ip.source_id
  FROM maps_metadata.ingest_process ip
  WHERE f.ingest_process_id = ip.id;
select * from maps_metadata.map_files where source_id is null;
DELETE FROM maps_metadata.map_files WHERE source_id IS NULL;
ALTER TABLE maps_metadata.map_files ALTER COLUMN source_id SET NOT NULL;

-- 5. Now re-key the parent, then finish the children.
ALTER TABLE maps_metadata.ingest_process ALTER COLUMN source_id SET NOT NULL;
ALTER TABLE maps_metadata.ingest_process DROP CONSTRAINT ingest_process_pkey;
ALTER TABLE maps_metadata.ingest_process
  DROP CONSTRAINT IF EXISTS ingest_process_source_id_unique;
ALTER TABLE maps_metadata.ingest_process ADD PRIMARY KEY (source_id);
ALTER TABLE maps_metadata.ingest_process DROP COLUMN id;
select * from maps_metadata.ingest_process;

select * from maps_metadata.ingest_process_tag;
ALTER TABLE maps_metadata.ingest_process_tag DROP CONSTRAINT pk_tag;
ALTER TABLE maps_metadata.ingest_process_tag DROP COLUMN ingest_process_id;
ALTER TABLE maps_metadata.ingest_process_tag
  ADD CONSTRAINT pk_tag PRIMARY KEY (source_id, tag);
ALTER TABLE maps_metadata.ingest_process_tag
  ADD CONSTRAINT ingest_process_tag_source_id_fkey FOREIGN KEY (source_id)
  REFERENCES maps_metadata.ingest_process(source_id);

ALTER TABLE maps_metadata.map_files
  DROP CONSTRAINT IF EXISTS map_files_ingest_process_id_object_id_key;
ALTER TABLE maps_metadata.map_files DROP COLUMN ingest_process_id;
ALTER TABLE maps_metadata.map_files
  ADD CONSTRAINT map_files_source_id_object_id_key UNIQUE (source_id, object_id);
ALTER TABLE maps_metadata.map_files
  ADD CONSTRAINT map_files_source_id_fkey FOREIGN KEY (source_id)
  REFERENCES maps_metadata.ingest_process(source_id) ON DELETE CASCADE;

-- 6. Recreate the views (no map_ingest_metadata).
CREATE OR REPLACE VIEW macrostrat_api.map_ingest AS
  SELECT * FROM maps_metadata.ingest_process;
CREATE OR REPLACE VIEW macrostrat_api.map_ingest_tags AS
  SELECT * FROM maps_metadata.ingest_process_tag;

CREATE OR REPLACE VIEW map_ingestion_api.maps AS
WITH tags AS (
  SELECT source_id, array_agg(tag)::text[] names
  FROM maps_metadata.ingest_process_tag GROUP BY source_id
)
SELECT s.source_id, s.slug, name, url, ref_year, scale, i.state,
       coalesce(tags.names, ARRAY[]::text[]) AS tags
FROM maps.sources s
LEFT JOIN maps_metadata.ingest_process i ON s.source_id = i.source_id
LEFT JOIN tags ON s.source_id = tags.source_id
ORDER BY s.source_id DESC;

GRANT SELECT, UPDATE ON maps_metadata.ingest_process TO web_user;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest TO web_user, web_admin;
GRANT SELECT, UPDATE ON macrostrat_api.map_ingest_tags TO web_user, web_admin;
GRANT SELECT ON macrostrat_api.map_ingest TO web_anon;
GRANT SELECT ON macrostrat_api.map_ingest_tags TO web_anon;
GRANT SELECT ON map_ingestion_api.maps TO web_anon;
GRANT SELECT, UPDATE, INSERT, DELETE ON macrostrat_api.map_ingest_tags TO web_admin;
NOTIFY pgrst, 'reload schema';