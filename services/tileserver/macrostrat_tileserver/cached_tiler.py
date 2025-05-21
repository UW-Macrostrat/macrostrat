from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlencode

from fastapi import BackgroundTasks, Depends, HTTPException, Query
from macrostrat.utils import get_logger
from morecantile import Tile
from starlette.requests import Request

from macrostrat.tileserver_utils import (
    TileParams,
    CacheMode,
    handle_cached_tile_request,
    MimeTypes,
    CachedTileArgs,
)
from timvt.factory import (
    TILE_RESPONSE_PARAMS,
    VectorTilerFactory,
    queryparams_to_kwargs,
)
from timvt.models.mapbox import TileJSON
from .function_layer import StoredFunction

log = get_logger(__name__)


class CachedVectorTilerFactory(VectorTilerFactory):
    def register_tiles(self):
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

            kwargs = queryparams_to_kwargs(
                request.query_params, ignore_keys=["tilematrixsetid"]
            )

            if not isinstance(layer, CachedStoredFunction):
                cache = CacheMode.bypass

            # "Table" layers don't have a validate_request method
            if hasattr(layer, "validate_request"):
                try:
                    await layer.validate_request(pool, tile, tms, **kwargs)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))

            args = CachedTileArgs(
                layer=layer,
                tile=tile,
                media_type=MimeTypes.pbf,
                params=kwargs,
                mode=cache,
            )

            async def get_tile(request: Request, args: CachedTileArgs):
                return await layer.get_tile(
                    request.app.state.pool, args.tile, args.tms, **args.params
                )

            return await handle_cached_tile_request(
                request,
                pool,
                background_tasks,
                get_tile,
                args,
            )

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
    profile_id: Optional[int] = None
