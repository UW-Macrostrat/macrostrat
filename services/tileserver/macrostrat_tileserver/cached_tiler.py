import decimal
import json
import typing
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode

from fastapi import BackgroundTasks, Depends, HTTPException, Query, Request
from macrostrat.utils import get_logger
from macrostrat.utils.timer import Timer
from morecantile import Tile
from starlette.requests import Request
from starlette.responses import JSONResponse
from timvt.dependencies import TileParams
from timvt.factory import (
    TILE_RESPONSE_PARAMS,
    VectorTilerFactory,
    queryparams_to_kwargs,
)
from timvt.models.mapbox import TileJSON
from buildpg import asyncpg, render

from .cache import get_tile_from_cache, set_cached_tile
from .function_layer import StoredFunction
from .utils import CacheMode, CacheStatus, TileResponse

log = get_logger(__name__)


class CachedVectorTilerFactory(VectorTilerFactory):

    async def get_cache_profile_id(self, pool, layer):
        if layer.profile_id is not None:
            return layer.profile_id
        # Set the cache profile id from the database
        async with pool.acquire() as conn:
            q, p = render(
                "SELECT id FROM tile_cache.profile WHERE name = :layer",
                layer=layer.id,
            )
            res = await conn.fetchval(q, *p)
            layer.profile_id = res
            return res

    def register_tiles(self):
        """Register /tiles endpoints."""

        @self.router.get("/{layer}/{z}/{x}/{y}", **TILE_RESPONSE_PARAMS)
        async def tile(
            request: Request,
            background_tasks: BackgroundTasks,
            tile: Tile = Depends(TileParams),
            TileMatrixSetId: Literal[
                tuple(self.supported_tms.list())
            ] = self.default_tms,
            layer=Depends(self.layer_dependency),
            cache: CacheMode = CacheMode.prefer,
            # If cache query arg is set, don't cache the tile
        ):
            """Return vector tile."""
            pool = request.app.state.pool
            tms = self.supported_tms.get(TileMatrixSetId)

            timer = Timer()

            kwargs = queryparams_to_kwargs(
                request.query_params, ignore_keys=["tilematrixsetid"]
            )

            should_cache = (
                isinstance(layer, CachedStoredFunction) and cache != CacheMode.bypass
            )

            if should_cache:
                profile = await self.get_cache_profile_id(pool, layer)
                content = await get_tile_from_cache(pool, profile, kwargs, tile, None)
                timer._add_step("check_cache")
                if content is not None:
                    return TileResponse(content, timer, cache_status=CacheStatus.hit)

            if cache == CacheMode.force:
                raise HTTPException(
                    status_code=404,
                    detail="Tile not found in cache",
                    header={
                        "Server-Timing": timer.server_timings(),
                        "X-Tile-Cache": CacheStatus.miss,
                    },
                )

            content = await layer.get_tile(pool, tile, tms, **kwargs)
            timer._add_step("get_tile")

            cache_status = CacheStatus.bypass
            if should_cache:
                profile = await self.get_cache_profile_id(pool, layer)
                background_tasks.add_task(
                    set_cached_tile, pool, profile, kwargs, tile, content
                )
                cache_status = CacheStatus.miss

            return TileResponse(content, timer, cache_status=cache_status)

        @self.router.get(
            "/{TileMatrixSetId}/{layer}/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        @self.router.get(
            "/{layer}/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        async def tilejson(
            request: Request,
            layer=Depends(self.layer_dependency),
            TileMatrixSetId: Literal[
                tuple(self.supported_tms.list())
            ] = self.default_tms,
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),
        ):
            """Return TileJSON document."""
            tms = self.supported_tms.get(TileMatrixSetId)

            path_params: Dict[str, Any] = {
                # "TileMatrixSetId": tms.id,
                "layer": layer.id,
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
            }
            tile_endpoint = self.url_for(request, "tile", **path_params)

            qs_key_to_remove = ["tilematrixsetid", "minzoom", "maxzoom"]
            query_params = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]

            if query_params:
                tile_endpoint += f"?{urlencode(query_params)}"

            # Get Min/Max zoom from layer settings if tms is the default tms
            if tms.id == layer.default_tms:
                minzoom = _first_value([minzoom, layer.minzoom])
                maxzoom = _first_value([maxzoom, layer.maxzoom])

            minzoom = minzoom if minzoom is not None else tms.minzoom
            maxzoom = maxzoom if maxzoom is not None else tms.maxzoom

            res = {
                "minzoom": minzoom,
                "maxzoom": maxzoom,
                "name": layer.id,
                "bounds": layer.bounds,
                "tiles": [tile_endpoint],
            }

            return res


def _first_value(values: List[Any], default: Any = None):
    """Return the first not None value."""
    return next(filter(lambda x: x is not None, values), default)


# Register endpoints.


class CachedStoredFunction(StoredFunction):
    profile_id: int | None = None


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


class DecimalJSONResponse(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=DecimalEncoder,
        ).encode("utf-8")
