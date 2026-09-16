/** This query gets matched strat names as text.

  The shape matters more than it looks. `{match_field}` is often a `concat_ws`
  of every text column on the table, so it is wide -- a thousand characters and
  up once `descrip` is populated -- and the query explodes it into words. Three
  things follow, and together they are the difference between a second and three
  minutes on a large map:

  1. **Deduplicate the text before exploding it.** The text describes a *map
     unit*, not a polygon, so a map with 216,462 polygons has 9,028 distinct
     texts and one with 6,317 has 53. Exploding per polygon does the same work
     tens or hundreds of times over.
  2. **Group on a hash, not on the text.** Deduplicating by sorting 216,462
     rows keyed on the text itself spills 350MB and takes 17 seconds; grouping
     on `md5` of it takes 1, and parallelizes.
  3. **Carry `match_text` no further than necessary.** Only the handful of rows
     this finally returns need it, so the per-word pass carries the id alone and
     the text is joined back at the end. Carrying it through cost 7GB of temp
     files on Alaska.
*/
WITH source_text AS (
  SELECT
    min({id_field}) AS map_id,
    min({match_field}) AS match_text
  FROM {match_table}
  WHERE
    source_id = :source_id
  GROUP BY md5({match_field})
),
/** Words that say nothing about which unit this is: lithologies, which are
  matched separately and properly, and the rank words every name ends in. */
stop_words AS (
  SELECT lower(lith) AS word FROM macrostrat.liths
  UNION ALL
  SELECT unnest(ARRAY['bed', 'member', 'formation', 'group', 'supergroup'])
),
filtered_words AS (
  /** One representative row per distinct word. The final `DISTINCT ON` keeps a
    single row per strat name regardless, so carrying every (word, polygon) pair
    through the join only to discard it is wasted sorting. */
  SELECT DISTINCT ON (w.word)
    w.word AS words,
    st.map_id
  FROM source_text st,
    LATERAL unnest(string_to_array(st.match_text, ' ')) AS w(word)
  WHERE w.word <> ''
    AND NOT EXISTS (
      SELECT 1 FROM stop_words s WHERE s.word = lower(w.word)
    )
  ORDER BY w.word, st.map_id
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
  st.match_text
FROM nearby_strat_names nsn
JOIN macrostrat.lookup_strat_names lsn
  ON nsn.strat_name_id = lsn.strat_name_id
JOIN filtered_words f
  ON nsn.words = f.words
JOIN source_text st
  ON st.map_id = f.map_id;
