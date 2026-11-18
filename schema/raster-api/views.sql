/** Admin management API for the raster index, served by PostgREST at
 * /api/v3/rasters/pg. Views run with their owner's rights, so web_admin needs
 * no grant on raster_layers itself. */

CREATE SCHEMA raster_api;
GRANT USAGE ON SCHEMA raster_api TO web_admin;

CREATE OR REPLACE VIEW raster_api.layers AS
SELECT
  l.slug,
  l.name,
  l.description,
  l.minzoom,
  l.maxzoom,
  l.rescale_range,
  (SELECT count(*) FROM raster_layers.raster r WHERE r.layer = l.slug) AS raster_count
FROM raster_layers.layer l;

-- Leaves out footprint and info: large, and not editable in a sheet.
CREATE OR REPLACE VIEW raster_api.rasters AS
SELECT
  id,
  layer,
  slug,
  href,
  substring(href FROM '^[a-z0-9]+://([^/]+)') AS host,
  minzoom,
  maxzoom,
  dtype,
  nbands,
  nodata,
  crs,
  rescale_range,
  created_at,
  updated_at
FROM raster_layers.raster;

GRANT SELECT, INSERT, UPDATE, DELETE ON raster_api.layers TO web_admin;
GRANT SELECT, DELETE ON raster_api.rasters TO web_admin;
-- Assignment to a layer is the only edit; everything else comes from the file.
GRANT UPDATE (layer) ON raster_api.rasters TO web_admin;

NOTIFY pgrst, 'reload schema';
