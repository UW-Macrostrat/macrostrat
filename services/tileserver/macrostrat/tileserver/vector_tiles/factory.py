"""Tile and TileJSON routes for stored-function layers.

Replaces `timvt.factory` (and the `CachedVectorTilerFactory` that wrapped it).
The two collapsed into one class: with tile-matrix negotiation and table layers
gone, there was nothing left in the base worth inheriting.

Routes are `/{layer}/{z}/{x}/{y}` and `/{layer}/tilejson.json`, the shapes
Macrostrat's clients already use.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from morecantile import Tile
from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import Response

from macrostrat.tileserver_utils import (
    CachedTileArgs,
    CacheMode,
    MimeTypes,
    TileParams,
    get_layer_id,
    handle_cached_tile_request,
)
from macrostrat.utils import get_logger

from .layers import StoredFunction

log = get_logger(__name__)

__all__ = ["VectorTileFactory", "TILE_RESPONSE_PARAMS", "queryparams_to_kwargs"]

TILE_RESPONSE_PARAMS: dict[str, Any] = {
    "responses": {200: {"content": {"application/x-protobuf": {}}}},
    "response_class": Response,
}


def queryparams_to_kwargs(q: QueryParams, ignore_keys: list = []) -> dict:
    """Query string to the parameter dict passed to the tile function.

    Repeated keys collapse to a list; everything else stays a scalar, which is
    what the SQL functions expect to find in their JSON argument.
    """
    values = {}
    for key in q.keys():
        if key in ignore_keys:
            continue
        items = q.getlist(key)
        values[key] = items if len(items) > 1 else items[0]
    return values


def layer_dependency(
    request: Request,
    layer: str = Path(..., description="Layer name"),
) -> StoredFunction:
    """Resolve a layer name against the application's function registry."""
    catalog = getattr(request.app.state, "function_catalog", None)
    found = catalog.get(layer) if catalog is not None else None
    if found is None:
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found.")
    return found


@dataclass
class VectorTileFactory:
    """Routes for every stored-function layer in the application's registry."""

    router: APIRouter = field(default_factory=APIRouter)
    # Needed to build absolute tile URLs when the router is mounted at a prefix.
    router_prefix: str = ""

    def __post_init__(self):
        self.register_tiles()

    def url_for(self, request: Request, name: str, **path_params: Any) -> str:
        """Absolute URL for one of this factory's endpoints."""
        url_path = self.router.url_path_for(name, **path_params)
        base_url = str(request.base_url)
        if self.router_prefix:
            base_url += self.router_prefix.lstrip("/")
        return str(url_path.make_absolute_url(base_url=base_url))

    def register_tiles(self):
        @self.router.get("/{layer}/{z}/{x}/{y}", **TILE_RESPONSE_PARAMS)
        async def tile(
            request: Request,
            background_tasks: BackgroundTasks,
            tile: Tile = Depends(TileParams),
            layer: StoredFunction = Depends(layer_dependency),
            cache: CacheMode = CacheMode.prefer,
        ):
            """Return a vector tile."""
            pool = request.app.state.pool
            kwargs = queryparams_to_kwargs(request.query_params, ignore_keys=["cache"])

            try:
                await layer.validate_request(pool, tile, **kwargs)
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err))

            # A layer with no cache profile is always served straight through.
            if layer.profile_id is None:
                cache = CacheMode.bypass

            layer_id = -1
            if cache != CacheMode.bypass:
                layer_id = await get_layer_id(pool, layer.profile_id)

            args = CachedTileArgs(
                layer=layer_id,
                tile=tile,
                media_type=MimeTypes.pbf,
                params=kwargs,
                mode=cache,
            )

            async def get_tile(request: Request, args: CachedTileArgs):
                return await layer.get_tile(
                    request.app.state.pool, args.tile, **args.params
                )

            return await handle_cached_tile_request(
                request, pool, background_tasks, get_tile, args
            )

        @self.router.get(
            "/{layer}/tilejson.json",
            responses={200: {"description": "Return a tilejson"}},
        )
        async def tilejson(
            request: Request,
            layer: StoredFunction = Depends(layer_dependency),
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),
        ):
            """Return a TileJSON document for a layer."""
            tile_endpoint = self.url_for(
                request, "tile", layer=layer.id, z="{z}", x="{x}", y="{y}"
            )

            # Carry the caller's query string onto the tile URLs, so a layer
            # parameterized in the tilejson request stays parameterized.
            dropped = ["minzoom", "maxzoom"]
            query_params = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in dropped
            ]
            if query_params:
                tile_endpoint += f"?{urlencode(query_params)}"

            return {
                "tilejson": "2.2.0",
                "name": layer.id,
                "bounds": layer.bounds,
                "minzoom": minzoom if minzoom is not None else layer.minzoom,
                "maxzoom": maxzoom if maxzoom is not None else layer.maxzoom,
                "tiles": [tile_endpoint],
            }
