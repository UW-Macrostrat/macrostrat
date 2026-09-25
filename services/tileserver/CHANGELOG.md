
## [Unreleased]

- `/map/{slug}/{z}/{x}/{y}`: tiles for any source by slug or id, `carto` included,
  resolved through `map_bounds.serving_source`; `/dev/carto` is a deprecated alias of
  `/map/carto`; `sys:carto-legacy` addresses the materialized build the same way
- Slugs other than `carto` require a delegated token with the `tiles:map` scope
- Tile cache: `/map/carto` under a `map-carto` profile; other slugs uncached
- Scale bands read from `map_bounds.scale_band` (cache manager)
- Compilation tiles: faces collected per map and clipped to the tile, polygons clipped and simplified to tile resolution before the transform, ownership clip only for polygons straddling a face edge (a z6 Midwest tile from 28 s to 6 s uncached)
- Removed the unmounted `single_map` module and the `carto_new` package
- Prune `maps.polygons` / `maps.lines` scale partitions in single-map tile queries
  and in `tile_layers.map()`, which scanned all four for every tile
- Fix: raster layers advertised tile URLs missing their mount prefix, so TileJSON
  and WMTS templates 404'd for anything that followed them (QGIS included)
- WMTS service on raster layers (`/WMTSCapabilities.xml`), advertising one layer per
  class so GIS clients can pick a mineral from a list
- Restrict raster layers to `WebMercatorQuad`: asset selection is Web Mercator by
  construction, so other grids selected assets for the wrong ground
- Scope the root `/{layer}/{z}/{x}/{y}` tile route to numeric tile addresses, so
  it stops shadowing four-segment raster routes (`/rasters/<layer>/point/...`)
- `?classes=Alunite,Muscovite` shorthand on categorical raster layers
- Carto v2 map tiles support
- Map ingestion tiles fixes
- Map bounds tile layer
