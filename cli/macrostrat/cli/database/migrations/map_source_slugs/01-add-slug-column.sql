/* Make the column naming scheme for map integration more consistent, while mostly preserving backwards compatibility (for now) */

-- Add a 'slug' column
ALTER TABLE maps.sources ADD COLUMN IF NOT EXISTS slug text UNIQUE;
COMMENT ON COLUMN maps.sources.slug IS 'Unique identifier for each Macrostrat source';

-- Set the new slugs column to the primary table column, minus the '_polygons' suffix
UPDATE maps.sources SET slug = primary_table WHERE slug IS NULL;

ALTER TABLE maps.sources ALTER COLUMN slug SET NOT NULL;
