"""The compilation graph -- maps assembled out of other maps.

A compilation is a map: a `maps.sources` row with members. There is no kind flag
anywhere, so these routes derive everything from `map_bounds.compilation_member`
and the functions beside it, exactly as `macrostrat compilations` does on the CLI
and as the tileserver's point-info route does per location. This is the same
graph, walked without a location.

Two routes, because the graph has two useful shapes: the whole thing at
compilation granularity (small -- the graph is the compilations, not the map
catalog), and one node with the edges on either side of it.
"""

from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Path as PathParam
from sqlalchemy import text

from api.database import DatabaseDep

from .models import (
    CompilationDetail,
    CompilationGraph,
    CompilationSummary,
    NeighborMap,
    NeighborResult,
)

router = APIRouter(prefix="/compilations", tags=["compilations"])

_queries = Path(__file__).parent / "queries"


def _query(name: str):
    return text((_queries / f"{name}.sql").read_text())


def location_params(
    lng: Annotated[
        Optional[float], Query(description="Longitude, to filter by coverage")
    ] = None,
    lat: Annotated[
        Optional[float], Query(description="Latitude, to filter by coverage")
    ] = None,
) -> dict:
    """An optional point, as bind parameters.

    Both or neither: a half-specified location is a mistake worth reporting
    rather than silently ignoring.
    """
    if (lng is None) != (lat is None):
        raise HTTPException(400, "Both 'lng' and 'lat' are required, or neither.")
    return {"lng": lng, "lat": lat}


LocationDep = Annotated[dict, Depends(location_params)]


@router.get("", summary="List compilations")
async def list_compilations(
    database: DatabaseDep, location: LocationDep
) -> list[CompilationSummary]:
    """Every compilation in the system, as the nodes of the compilation graph.

    Served tile layers are included -- a layer *is* a compilation, one that
    happens to be served -- because they are the roots most of the graph hangs
    from. The ordinary maps at the bottom are reached by expanding a node.

    Given `lng`/`lat`, only the compilations covering that point. A compilation
    covers a point when one of the maps it resolves to does, so the filtered set
    is closed upward and still assembles into the same tree.
    """
    async with database.async_connection() as conn:
        res = await conn.execute(_query("index"), location)
        return [CompilationSummary(**row) for row in res.mappings()]


@router.get("/graph", summary="The whole compilation graph")
async def get_graph(database: DatabaseDep, location: LocationDep) -> CompilationGraph:
    """Every node and edge of the hierarchy in one response.

    Declared before `/{ident}` so `graph` is not read as a slug.

    The graph is a few hundred of each — far smaller than the map catalog — so a
    client holds all of it and does its filtering, grouping and selection
    locally. That is the difference between this and walking `/{ident}` per
    level, which costs a request per level and can only ever show what has been
    expanded.

    Given `lng`/`lat`, only the nodes covering that point and the edges between
    them.
    """
    async with database.async_connection() as conn:
        res = await conn.execute(_query("graph"), location)
        row = res.mappings().first()

    return CompilationGraph(**row)


@router.get("/{ident}", summary="Show a compilation")
async def get_compilation(
    ident: Annotated[str, PathParam(description="Slug or source id")],
    database: DatabaseDep,
    location: LocationDep,
) -> CompilationDetail:
    """One map, with its members and the compilations that claim it.

    Accepts any map, not only a compilation: an ordinary map comes back with no
    members and whatever contains it, which answers "where does this map sit?"
    with the same route that answers "what is this compilation made of?".

    Given `lng`/`lat`, the members are pruned to those covering that point. The
    node's own `n_members` and `n_sources` stay global, so the denominator
    survives the filter.
    """
    source_id: Optional[int] = None
    if ident.isdigit():
        source_id = int(ident)

    async with database.async_connection() as conn:
        res = await conn.execute(
            _query("compilation"),
            {"ident": ident, "source_id": source_id, **location},
        )
        row = res.mappings().first()

    if row is None:
        raise HTTPException(404, f"No map matching '{ident}'")

    return CompilationDetail(**row)


@router.get("/{ident}/neighbors", summary="Other maps of this area")
async def get_neighbors(
    ident: Annotated[str, PathParam(description="Slug or source id")],
    database: DatabaseDep,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Most relevant neighbours to return")
    ] = 25,
    include_coarser: Annotated[
        bool,
        Query(description="Also return maps at coarser scales than this one"),
    ] = False,
) -> NeighborResult:
    """Maps whose footprint overlaps this one's, at this scale or finer.

    An area question rather than a point one: the subject is the map's own
    boundary, so this is polygon overlap against every other `map_area`.

    Ordered by *scale distance* first and coverage second — same-scale peers,
    then maps one band finer, and so on. Coarser maps are excluded unless asked
    for: every map is covered by the same handful of global and continental
    sheets, so including them puts identical answers on every page and buries the
    ones that mean something. Ordering by coverage alone did the same thing, by
    putting a global sheet covering 100% above a partner sheet covering 20%.

    This map's own membership chain is excluded in both directions — the
    compilations above it and the maps below it are membership facts, which the
    hierarchy states better and which `in_compilations` carries on every row.

    Lives here rather than under `/sources` because footprint reasoning is what
    this module owns, and because `/compilations/{ident}` already treats any map
    as addressable.
    """
    source_id: Optional[int] = None
    if ident.isdigit():
        source_id = int(ident)

    async with database.async_connection() as conn:
        res = await conn.execute(
            _query("neighbors"),
            {
                "ident": ident,
                "source_id": source_id,
                "limit": limit,
                "include_coarser": include_coarser,
                # Above this the overlap is skipped: cost scales with the
                # target's vertex count times the candidate count, and the one
                # map beyond it (`global2`, 1.4M points) measures at ~57 s for an
                # answer that amounts to "all of them".
                "max_points": 200_000,
            },
        )
        rows = res.mappings().all()

    identity = await _resolve_map(database, ident, source_id)
    if identity is None:
        raise HTTPException(404, f"No map matching '{ident}'")

    overlap_available = True
    if len(rows) > 0:
        overlap_available = bool(rows[0]["overlap_available"])

    return NeighborResult(
        source_id=identity["source_id"],
        slug=identity["slug"],
        overlap_available=overlap_available,
        include_coarser=include_coarser,
        neighbors=[NeighborMap(**row) for row in rows],
    )


async def _resolve_map(database, ident: str, source_id: Optional[int]):
    """A map's identity, so the response names its subject even when nothing
    overlaps it."""
    async with database.async_connection() as conn:
        res = await conn.execute(
            text(
                "SELECT source_id, slug FROM maps.sources"
                " WHERE slug = :ident OR source_id = :source_id"
            ),
            {"ident": ident, "source_id": source_id},
        )
        return res.mappings().first()
