DELETE FROM maps.map_strat_names msn
USING maps.polygons p
WHERE msn.map_id = p.map_id
AND p.source_id = :source_id
AND msn.basis_col NOT LIKE 'manual%';


DROP TABLE IF EXISTS temp_rocks;

/** Temporary, and session-scoped, which it was not.

  `CREATE TABLE` put this in the search path as an ordinary table, so two
  pipeline runs at once -- which `for_each_map` invites -- overwrote each other's
  match input, and a run that crashed left its rows behind for the next one to
  read before the `DROP` above. Every statement that touches it runs on the same
  `Database.session`, so a temporary table is visible to all of them and goes away
  on its own.
*/
CREATE TEMPORARY TABLE temp_rocks AS WITH first AS (
  SELECT
    row_number() OVER() as row_no,
    array_agg(map_id) AS map_ids,
    name,
    string_to_array(strat_name, ';') AS strat_name,
    age,
    lith,
    descrip,
    comments,
    t_interval,
    b_interval,
    ST_Envelope(ST_Collect(geom)) AS envelope
  FROM
    maps.polygons
  WHERE
    source_id = :source_id
  GROUP BY
    name,
    strat_name,
    age,
    lith,
    descrip,
    comments,
    t_interval,
    b_interval
),
with_nos AS (
  SELECT
    row_no,
    name,
    row_number() OVER() as name_no
  FROM
    (
      SELECT
        row_no,
        unnest(strat_name) AS name
      FROM
        first
    ) foo
),
name_parts AS (
  SELECT
    row_no,
    name_no,
    a.name_part,
    a.nr
  FROM
    with_nos
    LEFT JOIN LATERAL unnest(string_to_array(with_nos.name, ' ')) WITH ORDINALITY AS a(name_part, nr) ON TRUE
),
no_liths AS (
  SELECT
    row_no,
    name_no,
    name_part,
    nr
  FROM
    name_parts
  WHERE
    lower(name_part) NOT IN (
      select
        lower(lith)
      from
        macrostrat.liths
    )
    AND lower(name_part) NOT IN (
      'bed',
      'member',
      'formation',
      'group',
      'supergroup'
    )
),
clean AS (
  /** Reassemble the name from the words that survived, in their original order.

    The ordering has to be on the aggregate. An `ORDER BY` in the CTE above is
    not a guarantee that `array_agg` sees the rows that way -- Postgres may
    hash-aggregate or parallelise and discard it -- and when it does the words
    come out scrambled, so the twelve name-match passes downstream silently match
    something else. `nr` is the word's ordinality from `unnest(... WITH
    ORDINALITY)`, which is what the discarded `ORDER BY` was reaching for. */
  SELECT
    row_no,
    name_no,
    trim(array_to_string(array_agg(name_part ORDER BY nr), ' ')) AS name
  from
    no_liths
  GROUP BY
    name_no,
    row_no
)
SELECT
  map_ids,
  first.name,
  first.strat_name as orig_strat_name,
  trim(
    both ' '
    FROM
      replace(clean.name, '.', '')
  ) AS strat_name,
  trim(
    both ' '
    FROM
      clean.name
  ) AS strat_name_clean,
  age,
  lith,
  descrip,
  comments,
  t_interval,
  b_interval,
  envelope
FROM
  first
  LEFT JOIN clean ON first.row_no = clean.row_no;

CREATE INDEX ON temp_rocks (strat_name);
CREATE INDEX ON temp_rocks (strat_name_clean);
CREATE INDEX ON temp_rocks (t_interval);
CREATE INDEX ON temp_rocks (b_interval);
CREATE INDEX ON temp_rocks USING GiST (envelope);

DROP TABLE IF EXISTS temp_names;
