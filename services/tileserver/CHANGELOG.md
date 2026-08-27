
## [Unreleased]

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
