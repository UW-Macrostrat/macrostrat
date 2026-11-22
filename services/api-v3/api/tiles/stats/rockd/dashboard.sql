-- Rockd dashboard-load density, binned onto the H3 hexagonal grid.
--
-- Aggregated inline from usage_stats.rockd_dashboard_loads rather than from a
-- materialized grid: the data is spatially sparse, so pre-aggregation compresses
-- barely 2.6x at the base resolution while costing ~92 percent of the source row
-- count to maintain. Measured worst case is a couple of seconds, for a handful of
-- highly cacheable low-zoom tiles. Computing inline also means arbitrary date
-- ranges instead of fixed periods.
--
-- H3 rather than a tile-pyramid grid because these are positions of people, not
-- of tile requests, and get compared across regions on one colour ramp. A
-- web-Mercator cell's ground area goes as cos^2(latitude) -- 15x across the
-- latitudes this data spans -- whereas H3 res-9 cell area varies 1.34x and
-- non-monotonically.
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326) AS geographic_bbox,
    :resolution::int AS res
),
/*
Geographic bounds of the tile, widened by two cell edges.

Hexagons do not nest inside tiles, so a cell whose centroid lies outside the
tile can still overlap it; without the margin those cells drop out and leave
gaps along every tile seam.

The margin is applied in DEGREES, deliberately. Expanding the Mercator envelope
instead pushes past the world extent at the antimeridian, and ST_Transform then
wraps the longitude: the easternmost tile at z4 produced the envelope
[-179.53, 157.03], a box covering almost the whole globe EXCEPT the strip the
tile needs. The symptom was antimeridian tiles returning almost no data, with a
few stray cells bleeding in from the -180 side.

Longitude degrees shrink away from the equator, so the longitude margin is
divided by cos(latitude) to keep the ground distance roughly constant.
*/
bounds AS (
  SELECT
    mercator_bbox,
    res,
    ST_XMin(geographic_bbox) - lon_margin AS lon_lo,
    ST_XMax(geographic_bbox) + lon_margin AS lon_hi,
    greatest(ST_YMin(geographic_bbox) - lat_margin, -90) AS lat_lo,
    least(ST_YMax(geographic_bbox) + lat_margin, 90) AS lat_hi,
    -- Which side of the antimeridian this tile sits on, for un-wrapping the
    -- boundaries of any cell that straddles it (below).
    (ST_XMin(geographic_bbox) + ST_XMax(geographic_bbox)) / 2 < 0 AS western
  FROM tile,
  LATERAL (
    SELECT
      h3_get_hexagon_edge_length_avg(res, 'm') * 2 / 111320.0 AS lat_margin
  ) m,
  LATERAL (
    SELECT m.lat_margin / greatest(
      cos(radians((ST_YMin(geographic_bbox) + ST_YMax(geographic_bbox)) / 2)),
      0.05
    ) AS lon_margin
  ) n
),
/*
The margin can carry the range past +/-180. Rather than let that wrap, clamp the
primary envelope to the valid range and add a second envelope for the part that
spills over onto the other side. Both are tested with && against the same
indexed expression, so the planner can bitmap-OR two index scans.
*/
envelopes AS (
  SELECT
    mercator_bbox,
    res,
    western,
    ST_MakeEnvelope(
      greatest(lon_lo, -180), lat_lo, least(lon_hi, 180), lat_hi, 4326
    ) AS envelope,
    CASE
      WHEN lon_hi > 180
        THEN ST_MakeEnvelope(-180, lat_lo, lon_hi - 360, lat_hi, 4326)
      WHEN lon_lo < -180
        THEN ST_MakeEnvelope(lon_lo + 360, lat_lo, 180, lat_hi, 4326)
      ELSE NULL
    END AS wrapped_envelope
  FROM bounds
),
cells AS (
  SELECT
    h3_latlng_to_cell(POINT(l.lng, l.lat), e.res) AS cell,
    count(*)::bigint AS n_loads,
    count(DISTINCT l.client_id)::bigint AS n_clients
  FROM usage_stats.rockd_dashboard_loads l, envelopes e
  -- Matches the expression index rockd_dashboard_loads_geom exactly, so both
  -- branches plan as bitmap index scans rather than a sequential scan.
  -- The spatial test is parenthesised as a unit: AND binds tighter than OR, so
  -- without the outer parentheses the date filters would apply only to the
  -- wrapped branch.
  WHERE (
      (ST_SetSRID(ST_MakePoint(l.lng, l.lat), 4326) && e.envelope)
      OR (
        e.wrapped_envelope IS NOT NULL
        AND ST_SetSRID(ST_MakePoint(l.lng, l.lat), 4326) && e.wrapped_envelope
      )
    )
    AND (CAST(:start AS timestamptz) IS NULL OR l.time >= CAST(:start AS timestamptz))
    AND (CAST(:end AS timestamptz) IS NULL OR l.time < CAST(:end AS timestamptz))
  GROUP BY 1
  -- Optional floor on distinct clients per cell, off by default (min_clients=0)
  -- so the map shows the full dataset. See MIN_CLIENTS in __init__.py.
  HAVING count(DISTINCT l.client_id) >= :min_clients
)
SELECT ST_AsMVT(q, 'dashboard_loads', 4096, 'geom')
FROM (
  SELECT
    cells.n_loads,
    cells.n_clients,
    ST_AsMVTGeom(
      ST_Transform(
        /*
        A hexagon straddling the antimeridian comes back with vertices at both
        ~+179 and ~-179, which projects to a polygon smeared across the whole
        world. Detect it by span and make it contiguous: ST_ShiftLongitude maps
        the range to [0, 360], and western tiles are then translated back so the
        polygon lands beside them rather than 360 degrees away.
        */
        CASE
          WHEN ST_XMax(boundary) - ST_XMin(boundary) > 180 THEN
            CASE
              WHEN e.western THEN ST_Translate(ST_ShiftLongitude(boundary), -360, 0)
              ELSE ST_ShiftLongitude(boundary)
            END
          ELSE boundary
        END,
        3857
      ),
      e.mercator_bbox,
      4096, 0, true
    ) AS geom
  FROM cells, envelopes e,
  LATERAL (SELECT h3_cell_to_boundary_geometry(cells.cell) AS boundary) b
) AS q;
