-- Add unique constraint to map source names
-- We should eventually rename the column to `source_prefix`
ALTER TABLE maps.sources
ADD CONSTRAINT map_sources_name_key
UNIQUE (primary_table);