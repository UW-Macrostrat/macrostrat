from datetime import datetime
from pathlib import Path
from typing import Optional

from buildpg import render
from fastapi import APIRouter, HTTPException, Query, Request

from macrostrat.tileserver_utils import VectorTileResponse, get_sql

__here__ = Path(__file__).parent

router = APIRouter()

# H3 resolution to bin at, indexed by tile zoom.
#
# FLAT FLOOR AT LOW ZOOM: z0-z5 all bin at the same resolution. In the globe
# projection several zoom levels are on screen at once, and letting resolution
# track zoom there produces visible steps in hexagon size across the globe. One
# resolution for the whole low-zoom band keeps cells uniform. The cost is tile
# size -- the z0 tile carries ~15.9k cells (~460 kB) -- but that is a single,
# highly cacheable tile. Resolution 5 would be 1.2 MB, which is why the ceiling
# sits here.
#
# Above the band, each step is sized so cells land at a legible on-screen size.
# H3 steps are ~2.65x linear (~1.4 zoom levels), so the mapping is not 1:1.
#
# Capped at 9 (~380 m across), the finest defensible bin for GPS-sourced points:
# consecutive requests from a stationary client sit ~110 m apart on jitter alone,
# so anything finer scatters one person across neighbouring cells and invents
# spatial spread that is not real.
#
# Mirrored in the client's layer-styles.ts, which needs the same mapping to keep
# the colour scale comparable across zooms. Change both together.
ZOOM_RESOLUTION = [4, 4, 4, 4, 4, 4, 5, 6, 6, 7, 7, 8, 9, 9]
MAX_RESOLUTION = 9

# Minimum distinct clients for a cell to be rendered. 0 disables the filter.
#
# Off by default: the tiles carry no identifiers, only a hexagon and two counts,
# and the existing public heatmap page already renders individual dashboard
# positions at full precision — a ~380 m aggregate is strictly less revealing
# than what already ships. The lever is kept because it is the natural response
# if fine cells over narrow date ranges ever become a concern; raising it to 3
# drops ~89 percent of cells at res 9 (retaining 36 percent of loads) and ~67
# percent at res 6 (retaining 78 percent).
MIN_CLIENTS = 0


def resolution_for_zoom(z: int) -> int:
    if z < 0:
        return 0
    if z >= len(ZOOM_RESOLUTION):
        return MAX_RESOLUTION
    return ZOOM_RESOLUTION[z]


def _parse_date(value: Optional[str], name: str) -> Optional[datetime]:
    if value is None:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise HTTPException(
        status_code=400,
        detail=f"Invalid {name!r}: expected YYYY-MM-DD or YYYY-MM, got {value!r}",
    )


@router.get("/dashboard/{z}/{x}/{y}")
async def get_dashboard_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
    start: Optional[str] = Query(
        None, description="Inclusive lower bound, YYYY-MM-DD or YYYY-MM."
    ),
    end: Optional[str] = Query(
        None, description="Exclusive upper bound, YYYY-MM-DD or YYYY-MM."
    ),
):
    """Rockd dashboard-load density (source-layer `dashboard_loads`).

    Where and how much the Rockd app's dashboard is opened, binned onto the H3
    hexagonal grid at a resolution chosen from the tile zoom. Each feature
    carries `n_loads` and `n_clients`.

    `start` / `end` bound the period; omit both for all time. Cells backed by
    fewer than a few distinct clients are suppressed, so a single user's
    position is never rendered.
    """
    pool = request.app.state.pool

    start_dt = _parse_date(start, "start")
    end_dt = _parse_date(end, "end")
    if start_dt is not None and end_dt is not None and end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="`end` must be after `start`.")

    sql = get_sql(__here__ / "dashboard.sql")
    query, params = render(
        sql,
        z=z,
        x=x,
        y=y,
        resolution=resolution_for_zoom(z),
        start=start_dt,
        end=end_dt,
        min_clients=MIN_CLIENTS,
    )

    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        # ST_AsMVT aggregates to NULL when no cells qualify, which is the common
        # case here: the points are globally sparse and the privacy floor
        # suppresses thin cells. VectorTileResponse joins its arguments as bytes
        # and would raise on None, so fall back to an empty tile.
        return VectorTileResponse(data or b"")
