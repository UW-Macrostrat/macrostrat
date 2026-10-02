"""The elevation service: terrain height and bathymetry at a point or along a line.

Two routes, `GET /elevation/point/{lng},{lat}` and `GET /elevation/profile`,
over two interchangeable backends:

- **cog** — `macrostrat.raster_layers.sample_point` / `sample_line` over the
  `raster_layers` index: choose the rasters closest to the requested scale, read
  one decimated window per raster, decide validity by the mask so that neither
  a NaN nor SRTM's ocean-as-zero ever reaches a client as a height.
- **legacy** — the two SQL queries of the `elevation` Postgres database, exactly
  as `v2/elevation.ts` runs them today (`elevation/legacy.py`).

Which one answers is decided per environment, not per deploy: the COG backend
is used as soon as the index holds an elevation layer, and the legacy backend
until then, wherever `ELEVATION_DATABASE_URL` points at the old database. That
is what lets the legacy API switch to this service *before* any COG layer
exists, with identical answers, and each environment migrate by registering
layers. `?backend=cog|legacy` forces one, which is how parity is checked: two
answers from one server.

Mounted at `/elevation`, not under `/rasters`: the mosaic routes at
`/rasters/elevation` are titiler's, shaped for raster debugging, and stay
exactly as titiler defines them. These are the *service* — a plain JSON shape a
legacy pass-through reshapes trivially.

It lives in the tile server rather than in api-v3 because this is a raster read
with a JSON response instead of a PNG one: the raster libraries, the index
connection and the GDAL cache knobs are all here already. Should v3 present
elevation, it proxies.

The data is public (OpenTopography's SRTM products), so the routes are not
behind a delegated-token scope, unlike the `/rasters/*` mosaics.
"""

from os import environ
from time import monotonic
from typing import Literal, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Path, Query
from pydantic import BaseModel

from macrostrat.utils import get_logger

from .legacy import LEGACY_TABLES, LegacyElevation, LegacySample

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

# How long "does the index hold an elevation layer?" is remembered. Registering
# a layer is a rare, deliberate act, and this is checked on every request.
READINESS_TTL = 60.0

Backend = Literal["cog", "legacy"]


def supports_elevation() -> bool:
    """Whether the installed raster libraries carry the sampling primitives.

    The COG backend needs `macrostrat.raster_layers` 0.4 or later. On an older
    release the service still mounts if the legacy database is configured, so
    the library, this service and the legacy API can be upgraded in any order.
    """
    try:
        from macrostrat.raster_layers import sample_line, sample_point  # noqa: F401
    except ImportError:
        return False
    return True


# -- Response models -----------------------------------------------------------


class ElevationSource(BaseModel):
    """Which raster answered, and roughly how finely."""

    # An index layer, or `legacy` for the Postgres raster database.
    layer: str
    raster: Optional[str] = None
    # Approximate native ground sample distance in metres.
    resolution: Optional[float] = None


class ElevationPoint(BaseModel):
    lng: float
    lat: float
    # Metres above the geoid (EGM96 for both SRTM products); null where no
    # dataset covers the point, and so is `source`. Explicit nulls rather than
    # absent keys, so a client can tell "no coverage" from "old server".
    elevation: Optional[float]
    source: Optional[ElevationSource] = None
    backend: Backend


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
    # The ground sample distance the reads were made at, in metres. None for
    # the legacy backend, which reads native pixels.
    resolution: Optional[float]
    # Every raster that answered, in read order.
    sources: list[ElevationSource]
    backend: Backend


# -- Backend selection -----------------------------------------------------------


class ElevationBackends:
    """The two implementations, and the rule for choosing between them.

    Automatic selection prefers the index as soon as it holds any elevation
    layer, and falls back to the legacy database while it does not. Readiness
    is one small query, remembered for `READINESS_TTL`.
    """

    def __init__(
        self, index=None, legacy: Optional[LegacyElevation] = None, layers=None
    ):
        self.index = index
        self.legacy = legacy
        self.layers = list(layers or ELEVATION_LAYERS)
        self._ready: Optional[bool] = None
        self._ready_until = 0.0

    @property
    def available(self) -> list[str]:
        found = []
        if self.index is not None:
            found.append("cog")
        if self.legacy is not None:
            found.append("legacy")
        return found

    def cog_ready(self) -> bool:
        """Whether the index holds at least one of the elevation layers."""
        if self.index is None:
            return False
        now = monotonic()
        if self._ready is None or now > self._ready_until:
            registered = {layer.slug for layer in self.index.layers()}
            self._ready = any(slug in registered for slug in self.layers)
            self._ready_until = now + READINESS_TTL
        return self._ready

    def choose(self, requested: Optional[Backend]) -> Backend:
        if requested is not None:
            if requested not in self.available:
                raise HTTPException(
                    status_code=503,
                    detail=f"The {requested} elevation backend is not configured here",
                )
            return requested
        if self.cog_ready():
            return "cog"
        if self.legacy is not None:
            return "legacy"
        if self.index is not None:
            # No layers yet and no legacy database: answer honestly with nulls.
            return "cog"
        raise HTTPException(
            status_code=503, detail="No elevation backend is configured"
        )


def _legacy_source(sample: LegacySample) -> Optional[ElevationSource]:
    if sample.table is None:
        return None
    return ElevationSource(
        layer="legacy", raster=sample.table, resolution=LEGACY_TABLES.get(sample.table)
    )


# -- Routes --------------------------------------------------------------------


def build_elevation_router(
    index=None,
    legacy: Optional[LegacyElevation] = None,
    layers: Optional[list[str]] = None,
) -> APIRouter:
    """The two elevation routes, over whichever backends are given."""
    backends = ElevationBackends(index, legacy, layers)
    router = APIRouter()

    if index is not None:
        from macrostrat.raster_index import resolution_for_zoom
        from macrostrat.raster_layers import sample_line, sample_point

    def _cog_source(asset, latitude: float) -> Optional[ElevationSource]:
        if asset is None:
            return None
        resolution = None
        if asset.maxzoom is not None:
            resolution = round(resolution_for_zoom(asset.maxzoom, latitude=latitude), 1)
        return ElevationSource(
            layer=asset.layer, raster=asset.slug, resolution=resolution
        )

    backend_param = Query(
        None,
        description=(
            "Force a backend: `cog` (the raster index) or `legacy` (the elevation "
            "Postgres database). By default the index answers once it holds an "
            "elevation layer, and the legacy database until then."
        ),
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
                "closest to that scale rather than the finest available "
                "(raster index only)."
            ),
        ),
        backend: Optional[Backend] = backend_param,
    ):
        """Terrain height or water depth at a point, with the raster that supplied it.

        The finest dataset covering the point is read first; a masked pixel
        (nodata, or SRTM's ocean-as-zero) falls through to the next. `elevation`
        is null where nothing covers the point.
        """
        chosen = backends.choose(backend)
        if chosen == "legacy":
            sample = legacy.point(lng, lat)
            return ElevationPoint(
                lng=lng,
                lat=lat,
                elevation=sample.value,
                source=_legacy_source(sample),
                backend=chosen,
            )
        sample = sample_point(index, backends.layers, lng, lat, resolution=resolution)
        return ElevationPoint(
            lng=lng,
            lat=lat,
            elevation=sample.value,
            source=_cog_source(sample.source, lat),
            backend=chosen,
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
                "from its overviews instead of opening every fine tile it crosses "
                "(raster index only)."
            ),
        ),
        backend: Optional[Backend] = backend_param,
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
        chosen = backends.choose(backend)
        if chosen == "legacy":
            rows = legacy.profile((start_lng, start_lat), (end_lng, end_lat), samples)
            length = rows[-1].distance if rows else 0.0
            tables = []
            for row in rows:
                if row.table is not None and row.table not in tables:
                    tables.append(row.table)
            return ElevationProfile(
                samples=[
                    ProfileSample(
                        lng=r.lng,
                        lat=r.lat,
                        distance=round(r.distance, 1),
                        elevation=r.value,
                        source=_legacy_source(r),
                    )
                    for r in rows
                ],
                length=round(length, 1),
                spacing=round(length / max(samples - 1, 1), 1),
                resolution=None,
                sources=[
                    ElevationSource(
                        layer="legacy", raster=t, resolution=LEGACY_TABLES.get(t)
                    )
                    for t in tables
                ],
                backend=chosen,
            )

        result = sample_line(
            index,
            backends.layers,
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
                    source=_cog_source(s.source, s.lat),
                )
                for s in result.samples
            ],
            length=round(result.length, 1),
            spacing=round(result.spacing, 1),
            resolution=result.resolution,
            sources=[_cog_source(a, mid_lat) for a in result.assets],
            backend=chosen,
        )

    return router


def register_elevation_routes(
    app: FastAPI,
    database_url: Optional[str] = None,
    legacy_url: Optional[str] = None,
) -> bool:
    """Mount the elevation service at `/elevation`. Returns whether it was.

    `database_url` is the raster index (`DATABASE_URL`); `legacy_url` the old
    `elevation` database (`ELEVATION_DATABASE_URL`). Either alone is enough to
    mount; with both, the index answers once it holds an elevation layer.
    """
    index = None
    if supports_elevation():
        url = database_url or environ.get("DATABASE_URL")
        if url is None:
            log.warning("The raster index needs DATABASE_URL; elevation reads it not")
        else:
            from macrostrat.raster_index import RasterIndex

            # Synchronous, like the raster layers: rio-tiler's readers are
            # synchronous, so these are sync endpoints run in the threadpool.
            index = RasterIndex(url)
    else:
        log.warning(
            "macrostrat.raster_layers >= 0.4 is not installed; no COG elevation"
        )

    legacy = None
    legacy_url = legacy_url or environ.get("ELEVATION_DATABASE_URL")
    if legacy_url:
        legacy = LegacyElevation(legacy_url)

    if index is None and legacy is None:
        log.warning("No elevation backend is configured; routes not mounted")
        return False

    app.include_router(
        build_elevation_router(index, legacy),
        prefix=ELEVATION_PREFIX,
        tags=["Elevation"],
    )
    return True
