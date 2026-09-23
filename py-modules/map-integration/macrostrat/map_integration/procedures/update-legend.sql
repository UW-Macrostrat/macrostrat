-- Delete existing records
DELETE FROM
  maps.map_legend
WHERE
  legend_id IN (
    SELECT legend_id
    FROM maps.legend
    WHERE source_id = :source_id
  );

DELETE FROM
  maps.legend
WHERE
  source_id = :source_id;

-- Create legend
INSERT INTO
  maps.legend (
    source_id,
    name,
    strat_name,
    age,
    lith,
    descrip,
    comments,
    b_interval,
    t_interval
  )
SELECT
  DISTINCT ON (
    q.name,
    q.strat_name,
    q.age,
    q.lith,
    q.descrip,
    q.comments,
    q.b_interval,
    q.t_interval
  ) q.source_id,
  q.name,
  q.strat_name,
  q.age,
  q.lith,
  q.descrip,
  q.comments,
  q.b_interval,
  q.t_interval
FROM
  maps.polygons q
  LEFT JOIN maps.legend ON trim(COALESCE(legend.name, '')) = trim(COALESCE(q.name, ''))
  AND trim(COALESCE(legend.strat_name, '')) = trim(COALESCE(q.strat_name, ''))
  AND trim(COALESCE(legend.age, '')) = trim(COALESCE(q.age, ''))
  AND trim(COALESCE(legend.lith, '')) = trim(COALESCE(q.lith, ''))
  AND trim(COALESCE(legend.descrip, '')) = trim(COALESCE(q.descrip, ''))
  AND trim(COALESCE(legend.comments, '')) = trim(COALESCE(q.comments, ''))
  AND COALESCE(legend.b_interval, -999) = COALESCE(q.b_interval, -999)
  AND COALESCE(legend.t_interval, -999) = COALESCE(q.t_interval, -999)
  AND legend.source_id = q.source_id
WHERE
  q.source_id = :source_id
  AND legend_id IS NULL
/** Insert in a defined order, so `legend_id` is reproducible.

  `DISTINCT ON` fixes which row survives per key but says nothing about the order
  they are emitted in, and `legend_id` is a serial. Re-running this therefore gave
  the same legend entries different ids every time, which is why a run-to-run diff
  of `maps.legend` was meaningless and why everything keyed on `legend_id` had to
  be rebuilt whether or not anything had changed. Ordering on the key columns
  costs a sort `DISTINCT ON` was already paying for. */
ORDER BY
  q.name,
  q.strat_name,
  q.age,
  q.lith,
  q.descrip,
  q.comments,
  q.b_interval,
  q.t_interval;

INSERT INTO
  maps.map_legend (legend_id, map_id)
SELECT
  legend_id,
  map_id
FROM
  maps.polygons m
  JOIN maps.legend ON legend.source_id = m.source_id
  AND trim(COALESCE(legend.name, '')) = trim(COALESCE(m.name, ''))
  AND trim(COALESCE(legend.strat_name, '')) = trim(COALESCE(m.strat_name, ''))
  AND trim(COALESCE(legend.age, '')) = trim(COALESCE(m.age, ''))
  AND trim(COALESCE(legend.lith, '')) = trim(COALESCE(m.lith, ''))
  AND trim(COALESCE(legend.descrip, '')) = trim(COALESCE(m.descrip, ''))
  AND trim(COALESCE(legend.comments, '')) = trim(COALESCE(m.comments, ''))
  AND COALESCE(legend.b_interval, -999) = COALESCE(m.b_interval, -999)
  AND COALESCE(legend.t_interval, -999) = COALESCE(m.t_interval, -999)
WHERE
  m.source_id = :source_id;
