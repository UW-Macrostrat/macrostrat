from typing import List
from pathlib import Path

from buildpg import V, render
from fastapi import APIRouter, Request, Query
from os import environ
from httpx import AsyncClient
from contextvars import ContextVar
from json import dumps

client = AsyncClient()

from ..utils import scales_for_zoom, get_layer_sql, VectorTileResponse


router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/{model}/tiles/{z}/{x}/{y}")
async def get_tile(
    request: Request, model: str, z: int, x: int, y: int, term: str = Query(None)
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    if term:
        term, vector = await get_search_term_embedding(term, model)
    else:
        raise ValueError("No term provided")

    # Check if there is a query term in the cache and if not, add it

    mapsize, linesize = scales_for_zoom(z)

    params = dict(
        z=z,
        x=x,
        y=y,
        mapsize=mapsize,
        linesize=linesize,
        term_embedding=dumps(vector),
    )

    async with pool.acquire() as con:
        units_ = await run_layer_query(
            con, "units", compilation=V("carto.polygons"), **params
        )

    return VectorTileResponse(units_)


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(__here__ / "queries", layer_name)
    q, p = render(query, layer_name=layer_name, **params)
    return await con.fetchval(q, *p)


_term_index = ContextVar("term_index", default={})


async def get_search_term_embedding(term, model):
    """Get the embedding for a search term."""

    # Get the settings model
    from ..main import db_settings

    term_index = _term_index.get()
    if term in term_index:
        return term_index[term]

    url = db_settings.xdd_embedding_service_url

    data = {
        "inputs": [
            {
                "name": "prompt",
                "shape": [1],
                "datatype": "BYTES",
                "data": [term],
            }
        ]
    }

    response = await client.post(url, json=data, timeout=30)
    response.raise_for_status()

    vector = response.json()["outputs"][0]["data"]

    _term_index.set({**_term_index.get(), term: vector})

    return term, vector
