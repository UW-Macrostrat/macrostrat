DELETE FROM maps.map_strat_names msn
USING maps.polygons p
WHERE msn.map_id = p.map_id
AND p.source_id = :source_id
AND msn.basis_col NOT LIKE 'manual%';


DROP TABLE IF EXISTS temp_rocks;

CREATE TABLE temp_rocks AS WITH first AS (
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
    name_part
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
  order by
    nr
),
clean AS (
  SELECT
    row_no,
    name_no,
    trim(array_to_string(array_agg(name_part), ' ')) AS name
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
