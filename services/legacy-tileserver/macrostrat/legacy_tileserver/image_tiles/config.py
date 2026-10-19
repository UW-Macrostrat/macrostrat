"""Where carto's image tiles come from, and which scale draws each zoom.

`LEGACY_CARTO_FROM_COMPILATION`, the core tileserver's switch for `/carto` and
`/carto-slim`, selects the source here too, so an environment changes both with
one setting. Off, tiles are drawn from the legacy `carto.*` build in the zoom
bands it has always used; on, from the compilation system in the bands of
`map_bounds.scale_band`, read at startup.
"""

from os import environ


def carto_from_compilation() -> bool:
    value = environ.get("LEGACY_CARTO_FROM_COMPILATION", "")
    return value.strip().lower() in ("1", "true", "yes", "on")


# The legacy tileserver's bands, kept as served: medium runs to z9.
LEGACY_BANDS = [("tiny", 0), ("small", 3), ("medium", 6), ("large", 10)]

BANDS_QUERY = """
SELECT sb.scale::text AS scale, sb.min_zoom
FROM map_bounds.scale_band sb
ORDER BY sb.min_zoom
"""


class ScaleBands:
    """The scale bands in zoom order, as `(scale, min_zoom)`."""

    def __init__(self, bands):
        self.bands = sorted(bands, key=lambda b: b[1])
        if not self.bands or self.bands[0][1] != 0:
            raise ValueError("The scale bands must start at zoom 0")

    @classmethod
    def from_rows(cls, rows):
        return cls([(r["scale"], r["min_zoom"]) for r in rows])

    def band_for_zoom(self, zoom: int):
        band = self.bands[0]
        for b in self.bands:
            if zoom >= b[1]:
                band = b
        return band

    def scale_for_zoom(self, zoom: int) -> str:
        return self.band_for_zoom(zoom)[0]
