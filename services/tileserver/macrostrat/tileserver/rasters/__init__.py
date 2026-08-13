"""Raster mosaic layers, served from the `raster_layers` index.

Macrostrat's raster layers are declared here the way vector layers are declared
in the tileserver's `__init__`: as data. Everything else — asset selection,
compositing, rendering — belongs to `macrostrat.raster_index` /
`macrostrat.raster_layers`, which are deliberately kept at arm's length from the
rest of the tile server so raster work can be tested on its own.

The raster libraries are not yet released, so registration is optional: where
they aren't installed, the tile server starts without these routes.
"""

from os import environ
from typing import Optional

from fastapi import FastAPI

from macrostrat.utils import get_logger

log = get_logger(__name__)

__all__ = ["register_raster_routes", "RASTER_LAYERS"]


def raster_layer_configs():
    """Macrostrat's canned raster layers."""
    from macrostrat.raster_layers import RasterLayerConfig

    return [
        # Mineral maps derived from EMIT hyperspectral data (Zaid Al-Attar and
        # Thomas Monecke, Colorado School of Mines). Single-band Byte
        # classifications with an embedded palette: `nearest` resampling is
        # required — interpolating between class indices invents minerals — and
        # the colormap comes from the layer definition in the index.
        RasterLayerConfig(
            slug="emit-minerals",
            title="EMIT mineral maps",
            resampling="nearest",
        ),
    ]


# Kept as a module-level name for discoverability; built lazily because the
# config type comes from an optional dependency.
RASTER_LAYERS = raster_layer_configs


def register_raster_routes(app: FastAPI, database_url: Optional[str] = None) -> bool:
    """Mount raster layers under `/rasters`. Returns whether they were mounted."""
    try:
        from macrostrat.raster_index import RasterIndex
        from macrostrat.raster_layers import register_raster_layers
    except ImportError as err:
        log.warning("Raster layers are not available: %s", err)
        return False

    url = database_url or environ.get("DATABASE_URL")
    if url is None:
        log.warning("Raster layers need DATABASE_URL; skipping")
        return False

    # A synchronous index alongside the app's asyncpg pool: rio-tiler's readers
    # are synchronous, so these routes are sync `def` endpoints run in
    # Starlette's threadpool, where a sync engine is the right tool.
    index = RasterIndex(url)
    configs = raster_layer_configs()
    register_raster_layers(app, index, configs, prefix="/rasters", tags=["Rasters"])

    # Register cache invalidation routes for the raster layers.
    # TODO: we might move this, either into the layer config
    # or out into the cache management cluster of routes...
    for cfg in configs:
        prefix = f"rasters/{cfg.slug}"
        url = f"/{prefix}/refresh"

        def _invalidate_cache():
            from ..cache_management import _flush_l1_cache

            _flush_l1_cache(prefix)

        app.add_api_route(url, _invalidate_cache, methods=["POST"], tags=["Rasters"])

    return True
