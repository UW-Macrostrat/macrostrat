/** This query gets matched strat names as text */
WITH source_text AS (
  SELECT
    {match_field} match_text,
    {id_field} map_id
  FROM {match_table}
  WHERE
    source_id = :source_id
),
source_words AS (
  SELECT DISTINCT ON (words)
    unnest(string_to_array(match_text, ' ')) AS words,
    match_text,
    map_id
  FROM source_text
),
filtered_words AS (
  SELECT
    DISTINCT (words) words,
    map_id,
    match_text
  FROM
    source_words sub
  WHERE lower(words) NOT IN (
          SELECT lower(lith) FROM macrostrat.liths
        )
    AND lower(words) NOT IN (
      'bed',
      'member',
      'formation',
      'group',
      'supergroup'
    )
),
nearby_strat_names AS (
  SELECT DISTINCT
    lsn.strat_name_id,
    lsn.strat_name,
    unnest(string_to_array(lsn.rank_name, ' ')) AS words
  FROM macrostrat.lookup_strat_names AS lsn
  JOIN macrostrat.strat_name_footprints snf
    ON snf.strat_name_id = lsn.strat_name_id
  JOIN maps.sources
    ON ST_Intersects(snf.geom, rgeom)
  WHERE
    sources.source_id = :source_id
)
SELECT
  DISTINCT ON (nsn.strat_name_id)
  lsn.*,
  f.map_id,
  f.match_text
FROM nearby_strat_names nsn
JOIN macrostrat.lookup_strat_names lsn
  ON nsn.strat_name_id = lsn.strat_name_id
JOIN filtered_words f
  ON nsn.words = f.words;