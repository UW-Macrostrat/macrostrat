"""The legacy elevation backend: the `elevation` Postgres database, as it is.

Two SQL queries over `sources.srtm1` (SRTM GL1, 1 arcsec) and `sources.etopo1`
(1 arcmin topography and bathymetry), ported from `v2/elevation.ts` in
macrostrat-api with the response reshaped, nothing else. It exists so that the
`/elevation` routes can serve *today's* answers in an environment where no COG
layer has been registered yet — the legacy API can switch to this service
first, and each environment moves to the COG index by registering layers,
with no deploy and no config change in between.

Priority is the legacy one: SRTM first, etopo1 where SRTM has no value. The
point query does not filter zeros; the legacy profile query did
(`AND elevation != 0`, the ocean workaround), and that is kept here so the two
implementations agree byte for byte until the COG index replaces this one.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, text

from macrostrat.utils import get_logger

log = get_logger(__name__)

__all__ = ["LegacyElevation", "LegacySample", "LEGACY_TABLES"]

# Table name → approximate native resolution in metres, for the `source` field.
LEGACY_TABLES = {"srtm1": 30.0, "etopo1": 1852.0}

POINT_SQL = text(
    """
    WITH candidates AS (
      SELECT ST_Value(rast, 1, ST_SetSRID(ST_Point(:lng, :lat), 4326)) AS elevation,
             1 AS priority, 'srtm1' AS source
      FROM sources.srtm1
      WHERE ST_Intersects(ST_SetSRID(ST_Point(:lng, :lat), 4326), rast)
      UNION ALL
      SELECT ST_Value(rast, 1, ST_SetSRID(ST_Point(:lng, :lat), 4326)) AS elevation,
             2 AS priority, 'etopo1' AS source
      FROM sources.etopo1
      WHERE ST_Intersects(ST_SetSRID(ST_Point(:lng, :lat), 4326), rast)
    )
    SELECT elevation, source
    FROM candidates
    WHERE elevation IS NOT NULL
    ORDER BY priority
    LIMIT 1
"""
)

# `samples` points from start to end, linear in lon/lat, exactly as the legacy
# query lays them out; distance is spherical, from the start, in metres.
PROFILE_SQL = text(
    """
    WITH line AS (
      SELECT ST_SetSRID(ST_MakeLine(ST_Point(:x0, :y0), ST_Point(:x1, :y1)), 4326) AS geom
    ),
    points AS (
      SELECT i,
             ST_SetSRID((ST_Dump(
               ST_LocateAlong(ST_AddMeasure((SELECT geom FROM line), 0, :n - 1), i)
             )).geom, 4326) AS geom
      FROM generate_series(0, :n - 1) AS i
    )
    SELECT i,
           ST_X(p.geom) AS lng,
           ST_Y(p.geom) AS lat,
           ST_DistanceSphere(p.geom, ST_SetSRID(ST_Point(:x0, :y0), 4326)) AS distance,
           e.elevation,
           e.source
    FROM points p
    LEFT JOIN LATERAL (
      SELECT elevation, source
      FROM (
        SELECT ST_Value(rast, 1, p.geom) AS elevation, 1 AS priority, 'srtm1' AS source
        FROM sources.srtm1 WHERE ST_Intersects(p.geom, rast)
        UNION ALL
        SELECT ST_Value(rast, 1, p.geom) AS elevation, 2 AS priority, 'etopo1' AS source
        FROM sources.etopo1 WHERE ST_Intersects(p.geom, rast)
      ) candidates
      WHERE elevation IS NOT NULL AND elevation != 0
      ORDER BY priority
      LIMIT 1
    ) e ON true
    ORDER BY i
"""
)


@dataclass
class LegacySample:
    lng: float
    lat: float
    distance: float
    value: Optional[float]
    # `srtm1` or `etopo1`; None where neither had a value.
    table: Optional[str]


class LegacyElevation:
    """Point and profile queries against the legacy raster database."""

    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True)

    def point(self, lng: float, lat: float) -> LegacySample:
        with self.engine.connect() as conn:
            row = conn.execute(POINT_SQL, dict(lng=lng, lat=lat)).first()
        if row is None:
            return LegacySample(lng, lat, 0.0, None, None)
        return LegacySample(lng, lat, 0.0, float(row.elevation), row.source)

    def profile(
        self, start: tuple[float, float], end: tuple[float, float], samples: int
    ) -> list[LegacySample]:
        (x0, y0), (x1, y1) = start, end
        with self.engine.connect() as conn:
            rows = conn.execute(
                PROFILE_SQL, dict(x0=x0, y0=y0, x1=x1, y1=y1, n=samples)
            ).all()
        return [
            LegacySample(
                float(r.lng),
                float(r.lat),
                float(r.distance),
                None if r.elevation is None else float(r.elevation),
                r.source,
            )
            for r in rows
        ]
