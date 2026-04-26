
--delete ingest_process rows with NULL source_id.
DELETE FROM maps_metadata.ingest_process
WHERE source_id IS NULL;


--delete duplicate ingest_process rows and dependent FK rows first.
DELETE FROM maps_metadata.ingest_process_tag
WHERE ingest_process_id IN (
  668, 669, 670, 671,
  684,
  691, 692,
  716, 717, 720,
  733,
  747,
  805,
  807,
  809,
  811,
  1934,
  2068, 2078,
  2088
);


DELETE FROM maps_metadata.ingest_process
WHERE id IN (
  668, 669, 670, 671,
  684,
  691, 692,
  716, 717, 720,
  733,
  747,
  805,
  807,
  809,
  811,
  1934,
  2068, 2078,
  2088
);


ALTER TABLE maps_metadata.ingest_process_tag
DROP CONSTRAINT ingest_process_tag_ingest_process_id_fkey;

ALTER TABLE maps_metadata.ingest_process_tag
ADD CONSTRAINT ingest_process_tag_ingest_process_id_fkey
FOREIGN KEY (ingest_process_id)
REFERENCES maps_metadata.ingest_process(id)
ON UPDATE CASCADE
ON DELETE CASCADE;

select * from maps_metadata.map_files;

ALTER TABLE maps_metadata.map_files
DROP CONSTRAINT map_files_ingest_process_id_fkey;

ALTER TABLE maps_metadata.map_files
ADD CONSTRAINT map_files_ingest_process_id_fkey
FOREIGN KEY (ingest_process_id)
REFERENCES maps_metadata.ingest_process(id)
ON UPDATE CASCADE
ON DELETE CASCADE;

--Move ids out of the way to avoid collisions with source_id values.
UPDATE maps_metadata.ingest_process
SET id = id + 1000000000;

--Set ingest_process.id equal to source_id.
UPDATE maps_metadata.ingest_process
SET id = source_id;

--Enforce source_id as required and unique.
ALTER TABLE maps_metadata.ingest_process
ALTER COLUMN source_id SET NOT NULL;

ALTER TABLE maps_metadata.ingest_process
ADD CONSTRAINT ingest_process_source_id_unique UNIQUE (source_id);

--Add trigger to keep future rows synced.
CREATE OR REPLACE FUNCTION maps_metadata.sync_ingest_process_id_with_source_id()
RETURNS trigger AS $$
BEGIN
  IF NEW.source_id IS NULL THEN
    RAISE EXCEPTION 'source_id cannot be null because ingest_process.id is synced to source_id';
  END IF;

  NEW.id := NEW.source_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_ingest_process_id_with_source_id_trigger
ON maps_metadata.ingest_process;

CREATE TRIGGER sync_ingest_process_id_with_source_id_trigger
BEFORE INSERT OR UPDATE OF source_id
ON maps_metadata.ingest_process
FOR EACH ROW
EXECUTE FUNCTION maps_metadata.sync_ingest_process_id_with_source_id();

--Reset sequence.
SELECT setval(
  pg_get_serial_sequence('maps_metadata.ingest_process', 'id'),
  COALESCE((SELECT max(id) FROM maps_metadata.ingest_process), 1),
  true
);
