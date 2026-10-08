"""Which carto member draws each zoom.

Read from `map_bounds.scale_band` at startup, so the raster tiles change scale
where the vector tiles do; the 3/6/9 constants this file used to hold had
drifted from them (medium ran to z9 here).
"""

# Read once at startup: which carto member answers for each scale band.
BANDS_QUERY = """
SELECT
  sb.scale::text AS scale,
  sb.min_zoom,
  map_bounds.face_layer_for(map_bounds.resolve_source('carto'), sb.min_zoom) AS layer_id
FROM map_bounds.scale_band sb
ORDER BY sb.min_zoom
"""


class ScaleBands:
    """The scale bands in zoom order, each with the `map_layer` drawn for it."""

    def __init__(self, rows):
        self.bands = [
            (r["scale"], r["min_zoom"], r["layer_id"])
            for r in sorted(rows, key=lambda r: r["min_zoom"])
        ]
        if not self.bands or self.bands[0][1] != 0:
            raise ValueError("The scale bands must start at zoom 0")

    def band_for_zoom(self, zoom: int):
        band = self.bands[0]
        for b in self.bands:
            if zoom >= b[1]:
                band = b
        return band

    def scale_for_zoom(self, zoom: int) -> str:
        return self.band_for_zoom(zoom)[0]

    def layer_for_zoom(self, zoom: int):
        return self.band_for_zoom(zoom)[2]
