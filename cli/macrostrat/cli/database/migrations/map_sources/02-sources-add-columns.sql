ALTER TABLE maps.sources ADD COLUMN IF NOT EXISTS raster_url text;
ALTER TABLE maps.sources ADD COLUMN IF NOT EXISTS scale_denominator integer;
ALTER TABLE maps.sources ADD COLUMN IF NOT EXISTS is_finalized boolean DEFAULT false;
