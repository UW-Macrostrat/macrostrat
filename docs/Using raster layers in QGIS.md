# Using Macrostrat raster layers in QGIS

Macrostrat serves mosaicked raster datasets — the EMIT mineral maps, and other
layers as they are indexed — as map tiles from the tileserver. They can be loaded
into QGIS without a plugin, and **classified layers can be filtered to particular
classes on the server**, so you can put a single mineral on the map.

Two ways in. Use WMTS if you want to browse what is available; use an XYZ layer
if you already know exactly what you want, or you are scripting it.

Throughout, `emit-minerals` is the layer name and
`https://tiles.macrostrat.org` is the tileserver. For local development, swap in
`https://tiles.macrostrat.local`.

## The quick way: WMTS

**Layer ▸ Add Layer ▸ Add WMS/WMTS Layer…**, then **New** to create a
connection, and give it this URL:

```
https://tiles.macrostrat.org/rasters/emit-minerals/WMTSCapabilities.xml
```

Connect, and every mineral class appears as its own selectable layer. Pick one,
add it, done.

The layer names read as `TiTiler Mosaic_WebMercatorQuad_Alunite` — the tileserver
composes them and the mineral is the last part, so filtering the list by the
mineral name works.

**To get every class at once**, choose the layer named

```
TiTiler Mosaic_WebMercatorQuad_default
```

`default` here means "no class filter", not "a class called default". It sits in
the middle of the alphabetical list rather than at the top, so it is easy to
scroll past when you are looking for the whole mosaic.

## The precise way: an XYZ layer

**Layer ▸ Add Layer ▸ Add XYZ Layer…**, and build the URL from the tile
template. The whole mosaic:

```
https://tiles.macrostrat.org/rasters/emit-minerals/tiles/WebMercatorQuad/{z}/{x}/{y}@2x.png
```

Filter it by adding query parameters — one or more **classes**:

```
…/{z}/{x}/{y}@2x.png?classes=Alunite,Muscovite
```

a single source **dataset**:

```
…/{z}/{x}/{y}@2x.png?datasets=cali_clipped
```

or both together:

```
…/{z}/{x}/{y}@2x.png?classes=Alunite&datasets=cali_clipped
```

Anything outside the selection is drawn transparent, and the classes that remain
keep the layer's own colors, so several classes at once still read as a legend.
Separate multiple values with a plain comma. Class names containing spaces need
the space percent-encoded (`Basalt%20glass`), but the commas stay as they are.

## Finding the names to use

Both of these are plain JSON — open them in a browser.

**Class names** come from the layer's vocabulary:

```
https://tiles.macrostrat.org/rasters/emit-minerals/layer
```

The `categories` list gives each class's `value`, its `label` (the name to pass
to `?classes=`), and the `color` it is drawn in.

**Dataset names** come from the coverage footprints:

```
https://tiles.macrostrat.org/rasters/emit-minerals/footprints
```

Each feature's `properties.slug` is the name to pass to `?datasets=`, and its
`properties.href` is the underlying file — useful for the next section. The
footprints follow the actual data rather than each file's bounding box, so they
are also a fair picture of where a dataset really has coverage.

## What these layers can't do

Both routes hand QGIS **rendered images**. That is fine for looking at the data
and for making a map, but it means:

- **Identify will not return a class value.** Clicking a pixel gives you a color,
  not "Alunite".
- **You cannot restyle in QGIS.** The colors come from the palette stored with
  the layer, and classes are chosen on the server rather than toggled locally.

If you need the actual class values, open one of the source files directly
instead. GDAL reads a cloud-optimized GeoTIFF over HTTP, so in
**Layer ▸ Add Layer ▸ Add Raster Layer…**, choose the *Protocol* source type
(or type the path directly) and use the `href` from the footprints response,
prefixed with `/vsicurl/`:

```
/vsicurl/https://storage.macrostrat.org/remote-sensing-data/emit-mineral-maps/Group2min/cali_clipped.tif
```

QGIS then treats it as an ordinary paletted raster: the *Paletted/Unique values*
renderer lists the classes, you can show, hide and recolor them yourself, and
Identify returns the class value. The trade-off is that this is one file at a
time — no mosaicking, and you have to know which file covers your area.

## Other layers

The same URLs work for any indexed raster layer: substitute its name for
`emit-minerals`. The `?classes=` filter and the per-class WMTS layers only apply
to *classified* layers — ones whose pixels are class codes rather than continuous
measurements — and only once a class vocabulary has been recorded for them.
