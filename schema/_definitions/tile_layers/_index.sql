-- @subsystem: tile-layers
-- @depends-on: core, maps, map-topology
/**
 * Maps subsystem: source registry, map geometries, and carto views.
 *
 * Content is applied after this lead file, in filename order
 * (01-maps → 02-views → 03-carto → 04-carto_new).
 */

SET search_path = 'tile_layers', 'maps', 'map_bounds_topology', 'public';
