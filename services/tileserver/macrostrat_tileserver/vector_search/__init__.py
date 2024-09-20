from dataclasses import dataclass
from json import dumps
from typing import List
from pathlib import Path

from buildpg import V, render
from fastapi import APIRouter, Request, Query
from httpx import AsyncClient
from contextvars import ContextVar

client = AsyncClient()

from ..utils import scales_for_zoom, get_layer_sql, get_sql, VectorTileResponse

from macrostrat.utils import get_logger

log = get_logger(__name__)


async def on_startup(app):
    # Create the search term index
    pool = app.state.pool

    try:
        stmt = get_sql(__here__ / "queries" / "startup.sql")
        # Truncate the search term cache as we may have changed the math
        async with pool.acquire() as con:
            await con.execute(stmt)
    except Exception as e:
        log.error("Error refreshing vector search term cache")
        app.state.settings["vector_search_error"] = str(e)


router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/{model}/tiles/{z}/{x}/{y}")
async def get_tile(
    request: Request, model: str, z: int, x: int, y: int, term: str = Query(None)
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    if not term:
        raise ValueError("No term provided")

    # make sure we're not in an error state
    if "vector_search_error" in request.app.state.settings:
        raise ValueError(request.app.state.settings["vector_search_error"])

    model_name = standardize_model_name(model)

    term_id = await get_search_term_id(pool, term, model_name)

    # Check if there is a query term in the cache and if not, add it

    mapsize, linesize = scales_for_zoom(z)

    query = get_layer_sql(__here__ / "queries", "units")

    units_ = await fetchval(
        pool,
        query,
        z=z,
        x=x,
        y=y,
        mapsize=mapsize,
        model_name=model_name,
        linesize=linesize,
        term_id=term_id,
        layer_name="units",
    )

    return VectorTileResponse(units_)


class TermIndex(dict):
    index: ContextVar[dict] = ContextVar("term_index", default={})

    def get_term(self, model, term) -> int:
        return self.index.get().get(model, {}).get(term)

    def set_term(self, model: str, term: str, term_id: int):
        self.index.set(
            {
                **self.index.get(),
                model: {**self.index.get().get(model, {}), term: term_id},
            }
        )


_index = TermIndex()


async def get_search_term_id(pool, term, model) -> int:
    """Get the ID of a search term from the database, or create it if it doesn't exist."""

    term_id = _index.get_term(model, term)
    if term_id:
        return term_id

    # Check the database to see if the term exists
    term_id = await fetchval(
        pool,
        """
        SELECT sv.id FROM text_vectors.search_vector sv
        JOIN text_vectors.model m
          ON m.id = sv.model_id
        WHERE text = :term AND m.name = :model
        """,
        term=term,
        model=model,
    )

    if term_id:
        _index.set_term(model, term, term_id)
        return term_id

    # If the term doesn't exist, create it
    res = await get_search_term_embedding(term, model)

    ins_stmt = get_sql(__here__ / "queries" / "create-search-term.sql")
    term_id = await fetchval(
        pool,
        ins_stmt,
        text=term,
        model_name=res.model_name,
        model_version=res.model_version,
        sample_size=5000,
        text_vector=dumps(res.vector),
        norm_vector=dumps(res.norm_vector),
    )

    if term_id:
        _index.set_term(model, term, term_id)

    return term_id


async def fetchval(pool, query, **params):
    q, p = render(query, **params)
    async with pool.acquire() as con:
        return await con.fetchval(q, *p)


@dataclass
class XDDEmbeddingResponse:
    term: str
    model_name: str
    model_version: str
    vector: List[float]
    norm_vector: List[float]


async def get_search_term_embedding(term, model) -> XDDEmbeddingResponse:
    """Get the embedding for a search term from the xDD API."""

    # Get the settings model
    from ..main import db_settings

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
    res = response.json()
    vector = res["outputs"][0]["data"]

    # We don't query the model name properly at this point,
    # so we need to make sure it is standardized
    model_name = standardize_model_name(res.get("model_name"))
    assert model_name == model

    norm = sum(x**2 for x in vector) ** 0.5
    # Normalize the vector
    norm_vector = [x / norm for x in vector]
    # convert to list

    return XDDEmbeddingResponse(
        term=term,
        model_name=model_name,
        model_version=res.get("model_version"),
        vector=vector,
        norm_vector=norm_vector,
    )


def standardize_model_name(model_id: str) -> str:
    """Why can't we just all get along?"""
    if "/" not in model_id:
        return "iaross/" + model_id
    return model_id
