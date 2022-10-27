-- Add unique constraint to map source names
-- We should eventually rename the column to `source_prefix`
ALTER TABLE maps.sources
ADD CONSTRAINT map_sources_name_key
UNIQUE (primary_table);

-- Ensure that the source ID key is correctly autoincrementing
-- and restart with the correct value
BEGIN;
-- protect against concurrent inserts
LOCK TABLE maps.sources IN EXCLUSIVE MODE;
-- Update the sequence
SELECT setval('maps.sources_source_id_seq', COALESCE((SELECT max(source_id)+1 FROM maps.sources), 1), false);
COMMIT;