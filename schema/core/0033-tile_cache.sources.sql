/* The maps a cached tile draws, as source ids: what its `X-Macrostrat-Sources`
   header said when it was rendered, stored beside it so a cache hit carries
   the same header without asking the faces again. NULL for a tile cached
   before the column existed, or by a route that names no maps (the legacy
   carto build). The table is the postgis-tile-utils submodule's (0032), so the
   column is added here rather than in its CREATE TABLE. */
ALTER TABLE tile_cache.tile ADD COLUMN sources integer[];
