"""The elevation service: terrain height and bathymetry at a point or along a line.

Two routes, thin on top of `macrostrat.raster_layers.sample_point` and
`sample_line`, which do the work: choose the rasters closest to the requested
scale from the `raster_layers` index, read one decimated window per raster, and
decide validity by the mask so that neither a NaN nor SRTM's ocean-as-zero ever
reaches a client as a height.

Mounted at `/elevation`, not under `/rasters`: the mosaic routes at
`/rasters/elevation` are titiler's, shaped for raster debugging (per-asset value
arrays, band names), and stay exactly as titiler defines them. These are the
*service* — a plain JSON shape a legacy pass-through can reshape trivially —
and the difference between the two shapes is the reason this module exists.

It lives in the tile server rather than in api-v3 because this is a raster read
with a JSON response instead of a PNG one: the raster libraries, the index
connection and the GDAL cache knobs are all here already, and standing up a
second GDAL runtime elsewhere to answer the same question would be worse than
an inaccurate service name. Should v3 present elevation, it proxies.

The data is public (OpenTopography's SRTM products), so the routes are not
behind a delegated-token scope, unlike the `/rasters/*` mosaics.
"""

from os import environ
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Path, Query
from pydantic import BaseModel

from macrostrat.utils import get_logger

log = get_logger(__name__)

__all__ = [
    "ELEVATION_LAYERS",
    "ELEVATION_PREFIX",
    "register_elevation_routes",
    "build_elevation_router",
    "supports_elevation",
]

# The indexed layers composited for elevation, finest first. Registered by the
# `Topography` pipeline in `data-integration`: SRTM GL1 (1 arcsec, land only,
# ocean stored as 0 and masked by a nodata override) over SRTM15+ (15 arcsec,
# global topography *and* bathymetry). Layer order is the outer priority key;
# the scale window decides within it.
ELEVATION_LAYERS = ["srtm-gl1", "srtm15plus"]

ELEVATION_PREFIX = "/elevation"

# The legacy service sampled 201 points; a client may ask for more, within
# reason. Windows are read at the sample spacing, so cost grows with samples.
DEFAULT_SAMPLES = 201
MAX_SAMPLES = 2000


def supports_elevation() -> bool:
    """Whether the installed raster libraries carry the sampling primitives.

    The routes need `macrostrat.raster_layers` 0.4 or later. On an older
    release the tile server starts without them rather than failing, so the
    library and this service can be upgraded in either order.
    """
    try:
        from macrostrat.raster_layers import sample_line, sample_point  # noqa: F401
    except ImportError:
        return False
    return True


# -- Response models -----------------------------------------------------------


class ElevationSource(BaseModel):
    """Which raster answered, and roughly how finely."""

    layer: str
    raster: Optional[str] = None
    # Approximate native ground sample distance in metres, from the raster's
    # native zoom at the sample's latitude.
    resolution: Optional[float] = None


class ElevationPoint(BaseModel):
    lng: float
    lat: float
    # Metres above the geoid (EGM96 for both SRTM products); null where no
    # dataset covers the point, and so is `source`. Explicit nulls rather than
    # absent keys, so a client can tell "no coverage" from "old server".
    elevation: Optional[float]
    source: Optional[ElevationSource] = None


class ProfileSample(BaseModel):
    lng: float
    lat: float
    # Metres along the line from its start.
    distance: float
    elevation: Optional[float]
    source: Optional[ElevationSource] = None


class ElevationProfile(BaseModel):
    samples: list[ProfileSample]
    # Great-circle length of the line and spacing between samples, in metres.
    length: float
    spacing: float
    # The ground sample distance the reads were made at, in metres.
    resolution: Optional[float]
    # Every raster the index selected for the line, in read order.
    sources: list[ElevationSource]


# -- Routes --------------------------------------------------------------------


def build_elevation_router(index, layers: Optional[list[str]] = None) -> APIRouter:
    """The two elevation routes, bound to a raster index."""
    from macrostrat.raster_index import resolution_for_zoom
    from macrostrat.raster_layers import sample_line, sample_point

    layers = layers or ELEVATION_LAYERS
    router = APIRouter()

    def _source(asset, latitude: float) -> Optional[ElevationSource]:
        if asset is None:
            return None
        resolution = None
        if asset.maxzoom is not None:
            resolution = round(resolution_for_zoom(asset.maxzoom, latitude=latitude), 1)
        return ElevationSource(
            layer=asset.layer, raster=asset.slug, resolution=resolution
        )

    @router.get(
        "/point/{lng},{lat}",
        response_model=ElevationPoint,
        summary="Elevation at a point",
    )
    def point(
        lng: float = Path(description="Longitude, WGS84", ge=-180, le=180),
        lat: float = Path(description="Latitude, WGS84", ge=-90, le=90),
        resolution: Optional[float] = Query(
            None,
            gt=0,
            description=(
                "Target ground sample distance in metres. Chooses the dataset "
                "closest to that scale rather than the finest available."
            ),
        ),
    ):
        """Terrain height or water depth at a point, with the raster that supplied it.

        The finest dataset covering the point is read first; a masked pixel
        (nodata, or SRTM's ocean-as-zero) falls through to the next. `elevation`
        is null where nothing covers the point.
        """
        sample = sample_point(index, layers, lng, lat, resolution=resolution)
        return ElevationPoint(
            lng=lng, lat=lat, elevation=sample.value, source=_source(sample.source, lat)
        )

    @router.get(
        "/profile",
        response_model=ElevationProfile,
        summary="Elevation along a line",
    )
    def profile(
        start_lng: float = Query(ge=-180, le=180),
        start_lat: float = Query(ge=-90, le=90),
        end_lng: float = Query(ge=-180, le=180),
        end_lat: float = Query(ge=-90, le=90),
        samples: int = Query(
            DEFAULT_SAMPLES, ge=2, le=MAX_SAMPLES, description="Evenly spaced samples"
        ),
        resolution: Optional[float] = Query(
            None,
            gt=0,
            description=(
                "Target ground sample distance in metres. Defaults to the sample "
                "spacing, which is what lets a long profile read a coarse dataset "
                "from its overviews instead of opening every fine tile it crosses."
            ),
        ),
    ):
        """Elevation at evenly spaced points from start to end.

        Points are interpolated linearly in longitude and latitude, in the order
        given; distances are great-circle, from the start. Not split at the
        antimeridian.
        """
        if abs(end_lng - start_lng) > 180:
            raise HTTPException(
                status_code=422, detail="Profiles are not split at the antimeridian"
            )
        result = sample_line(
            index,
            layers,
            (start_lng, start_lat),
            (end_lng, end_lat),
            samples=samples,
            resolution=resolution,
        )
        mid_lat = (start_lat + end_lat) / 2
        return ElevationProfile(
            samples=[
                ProfileSample(
                    lng=s.lng,
                    lat=s.lat,
                    distance=round(s.distance, 1),
                    elevation=s.value,
                    source=_source(s.source, s.lat),
                )
                for s in result.samples
            ],
            length=round(result.length, 1),
            spacing=round(result.spacing, 1),
            resolution=result.resolution,
            sources=[_source(a, mid_lat) for a in result.assets],
        )

    return router


def register_elevation_routes(app: FastAPI, database_url: Optional[str] = None) -> bool:
    """Mount the elevation service at `/elevation`. Returns whether it was."""
    if not supports_elevation():
        log.warning(
            "Elevation routes need macrostrat.raster_layers >= 0.4; not mounted"
        )
        return False

    from macrostrat.raster_index import RasterIndex

    url = database_url or environ.get("DATABASE_URL")
    if url is None:
        log.warning("Elevation routes need DATABASE_URL; skipping")
        return False

    # Synchronous, like the raster layers: rio-tiler's readers are synchronous,
    # so these are sync endpoints run in Starlette's threadpool.
    index = RasterIndex(url)
    app.include_router(
        build_elevation_router(index), prefix=ELEVATION_PREFIX, tags=["Elevation"]
    )
    return True
