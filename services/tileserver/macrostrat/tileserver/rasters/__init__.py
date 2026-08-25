"""Raster mosaic layers, served from the `raster_layers` index.

Macrostrat's raster layers are declared here the way vector layers are declared
in the tileserver's `__init__`: as data. Everything else — asset selection,
compositing, rendering — belongs to `macrostrat.raster_index` /
`macrostrat.raster_layers`, which are deliberately kept at arm's length from the
rest of the tile server so raster work can be tested on its own.

Registration is optional: where the raster libraries aren't installed, the tile
server starts without these routes.

Two things are Macrostrat-specific and live here rather than in the libraries:
the `?classes=` shorthand on categorical layers (see `_class_filter_dependency`),
and a WMTS service advertising one layer per class, so GIS clients can pick a
mineral from a list instead of hand-editing a URL (see `_class_renders`).
"""

from dataclasses import dataclass
from os import environ
from typing import Optional

from fastapi import Depends, FastAPI, Query
from typing_extensions import Annotated

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


def _class_filter_dependency():
    """Macrostrat's `?classes=` shorthand for the class-filtering algorithm.

    The generic form is `?algorithm=classes&algorithm_params={"classes":[...]}` —
    portable, self-describing, and awkward to type. Since Macrostrat's raster
    layers are overwhelmingly categorical, this tile server accepts the flat form
    too, which is what makes a hand-configured map style readable. Both appear in
    the OpenAPI spec, and the generic form still wins if somebody sends both.

    This lives here rather than in `macrostrat.raster_layers` because it is a
    convenience of *this* application: a client pointed at some other tile server
    would find `?classes=` silently ignored, whereas the generic form either
    works or fails loudly.

    Built as a closure so the optional raster libraries are imported when routes
    are constructed, not when this module is imported.
    """
    from macrostrat.raster_layers import ClassFilter, categorical_algorithms

    # `Algorithms.dependency` builds a fresh function per access, so it has to be
    # captured once — otherwise FastAPI sees a new dependency on every call.
    standard_algorithms = categorical_algorithms().dependency

    def class_filter_params(
        classes: Annotated[
            Optional[str],
            Query(
                description=(
                    "Comma-separated classes to show, by name — e.g. "
                    "`classes=Alunite,Muscovite`. Everything else in the tile is "
                    "masked. Shorthand for `algorithm=classes`; names come from "
                    "the layer's vocabulary (`GET /rasters/{layer}/layer`), and "
                    "an unknown one is a 400."
                ),
            ),
        ] = None,
        algorithm=Depends(standard_algorithms),
    ):
        # An explicit `?algorithm=` is the more specific request, so it wins.
        if algorithm is not None or not classes:
            return algorithm

        names = [name.strip() for name in classes.split(",") if name.strip()]
        if not names:
            return None
        return ClassFilter(classes=names)

    return class_filter_params


def _supported_tms():
    """The tile grids these layers serve: WebMercatorQuad, and only that.

    Not a cosmetic restriction. Asset selection computes a tile's extent with
    `ST_TileEnvelope`, which is Web Mercator by definition, so a request in any
    other grid would select assets for the wrong patch of ground. titiler
    advertises every grid morecantile knows by default, so this closes a latent
    bug as well as keeping the WMTS document to a sane size — the default list
    produced 746 KB of Capabilities for *four* layers.
    """
    import morecantile
    from morecantile.defaults import TileMatrixSets

    return TileMatrixSets({"WebMercatorQuad": morecantile.tms.get("WebMercatorQuad")})


def _class_renders(index, layer_slugs):
    """One WMTS layer per class, so GIS clients can pick a mineral from a list.

    WMTS has no way to filter a layer by pixel value — no OGC standard does — and
    the standardized equivalent is to advertise each class as its own layer.
    That turns "show me only Alunite" from a URL a user has to hand-edit into an
    entry in QGIS's Add WMTS dialog, which is the whole point of serving WMTS at
    all.

    Resolved per Capabilities request rather than at startup, so classes added to
    the layer later show up without a restart.
    """

    def get_renders(src_dst):
        for slug in layer_slugs:
            categories = index.get_categories(slug)
            if categories:
                return {c.label: {"classes": c.label} for c in categories}
        return {}

    return get_renders


def _layer_router(config, index):
    """One layer's routes: the mosaic, the `?classes=` shorthand, and WMTS.

    `RasterLayerConfig.router` would build most of this, but both the shorthand
    and the WMTS extension need to reach the factory, so it is constructed here.
    """
    from titiler.mosaic.extensions.wmts import wmtsExtension

    from macrostrat.raster_layers import RasterMosaicFactory, fixed_layers

    overrides = {}
    if config.class_filtering:
        # Our dependency covers both `?classes=` and the generic `?algorithm=`,
        # so the library's own registration must not overwrite it.
        overrides["class_filtering"] = False
        overrides["process_dependency"] = _class_filter_dependency()

    factory = RasterMosaicFactory(
        index=index,
        path_dependency=fixed_layers(*config.layer_slugs),
        dataset_dependency=_dataset_params(config.resampling),
        default_colormap=config.colormap,
        use_index_colormap=config.use_index_colormap,
        backend_options=config.backend_options,
        optional_headers=config.optional_headers,
        supported_tms=_supported_tms(),
        extensions=[
            wmtsExtension(get_renders=_class_renders(index, config.layer_slugs))
        ],
        **overrides,
    )
    return factory.router


def _dataset_params(resampling: str):
    """titiler's dataset parameters with this layer's resampling default.

    Categorical rasters must stay `nearest` — interpolating between class indices
    invents minerals — while `?resampling=` still overrides it.
    """
    from rio_tiler.types import RIOResampling
    from titiler.core.dependencies import DatasetParams

    @dataclass
    class LayerDatasetParams(DatasetParams):
        resampling_method: Annotated[
            RIOResampling,
            Query(
                alias="resampling",
                description=f"RasterIO resampling algorithm. Defaults to `{resampling}`.",
            ),
        ] = resampling

    return LayerDatasetParams


def register_raster_routes(app: FastAPI, database_url: Optional[str] = None) -> bool:
    """Mount raster layers under `/rasters`. Returns whether they were mounted."""
    try:
        from macrostrat.raster_index import RasterIndex
        from macrostrat.raster_layers import install_exception_handlers
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

    # Mounted per layer rather than through `register_raster_layers`, so the
    # `?classes=` shorthand can be wired in. The exception handlers are the other
    # half of what that function does, and they are needed either way: without
    # them a tile past the edge of coverage is a 5xx.
    install_exception_handlers(app)
    for config in configs:
        app.include_router(
            _layer_router(config, index),
            prefix=f"/rasters/{config.slug}",
            tags=["Rasters"],
        )

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
