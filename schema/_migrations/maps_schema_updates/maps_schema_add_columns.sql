
ALTER TABLE maps.sources
RENAME COLUMN licence TO license;

ALTER TABLE maps.sources
ADD COLUMN IF NOT EXISTS keywords text[];

ALTER TABLE maps.sources
ADD COLUMN IF NOT EXISTS language text;

ALTER TABLE maps.sources
ADD COLUMN IF NOT EXISTS  description varchar;

ALTER TABLE maps.sources
ADD COLUMN IF NOT EXISTS date_finalized timestamptz;

ALTER TABLE maps.sources
ADD COLUMN IF NOT EXISTS ingested_by text;