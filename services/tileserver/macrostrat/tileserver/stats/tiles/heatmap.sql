-- Spatial heatmap of tile-request density from tileserver_stats.location_index.
--
-- location_index aggregates each request into a z<=8 cell (requests above z8 are
-- folded into the z8 cell that contains them). We use the z=8 layer — the finest,
-- and the one that absorbs all high-zoom requests — and re-bin it to a few levels
-- finer than the requested tile, so every tile carries a bounded grid of cells
-- (~256 max) whose `num_requests` drives the heatmap intensity client-side.
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    least(:z + 4, 8)::int AS lz  -- render resolution: a few levels below the view, capped at the z8 data
),
cells AS (
  SELECT
    (li.x >> (8 - tile.lz)) AS bx,
    (li.y >> (8 - tile.lz)) AS by,
    sum(li.num_requests)::bigint AS num_requests
  FROM tileserver_stats.location_index li, tile
  WHERE li.z = 8
    -- Organic traffic only: exclude known automated clients (cache-warmers /
    -- scrapers) so the heatmap reflects real usage, not machine traffic.
    AND NOT li.is_bot
    AND CASE WHEN :z <= 8 THEN
              -- z8 cells contained in the requested tile
              li.x >= (:x::bigint << (8 - :z)) AND li.x < ((:x::bigint + 1) << (8 - :z))
          AND li.y >= (:y::bigint << (8 - :z)) AND li.y < ((:y::bigint + 1) << (8 - :z))
        ELSE
              -- past z8 there is no finer data: the one z8 cell covering this tile
              li.x = (:x >> (:z - 8)) AND li.y = (:y >> (:z - 8))
        END
  GROUP BY 1, 2
)
SELECT ST_AsMVT(q, 'requests', 4096, 'geom')
FROM (
  SELECT
    cells.num_requests,
    ST_AsMVTGeom(
      ST_TileEnvelope(tile.lz, cells.bx, cells.by),
      tile.mercator_bbox,
      4096, 0, true
    ) AS geom
  FROM cells, tile
) AS q;
