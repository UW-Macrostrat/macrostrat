
WITH clean AS (
    SELECT collection_no, lower(regexp_replace(regexp_replace(replace(replace(grp, '.', ''), '"', ''), '\(\.*\)', ''), '\s+$', '')) AS name
    FROM macrostrat.pbdb_collections_new
),
unnested AS (
    SELECT collection_no, a.name_part, a.nr
    FROM clean
    LEFT JOIN LATERAL unnest(string_to_array(name, ' '))
    WITH ORDINALITY AS a(name_part, nr) ON TRUE
),
cleaned AS (
    SELECT collection_no, array_to_string(array_agg(name_part), ' ') AS cleaned_name
    FROM unnested
    WHERE lower(name_part) NOT IN ('supergroup', 'group', 'subgroup', 'formation', 'member', 'bed', 'beds', 'and', 'upper', 'middle', 'lower') AND
        lower(name_part) NOT IN (
            SELECT lower(lith)
            FROM macrostrat.liths
            UNION ALL
            SELECT lower(concat(lith, 's'))
            FROM macrostrat.liths
        )
    GROUP BY collection_no
)
UPDATE macrostrat.pbdb_collections_new SET grp_clean = cleaned_name
FROM cleaned
WHERE cleaned.collection_no = pbdb_collections_new.collection_no;

WITH clean AS (
    SELECT collection_no, lower(regexp_replace(regexp_replace(replace(replace(formation, '.', ''), '"', ''), '\(\.*\)', ''), '\s+$', '')) AS name
    FROM macrostrat.pbdb_collections_new
),
unnested AS (
    SELECT collection_no, a.name_part, a.nr
    FROM clean
    LEFT JOIN LATERAL unnest(string_to_array(name, ' '))
    WITH ORDINALITY AS a(name_part, nr) ON TRUE
),
cleaned AS (
    SELECT collection_no, array_to_string(array_agg(name_part), ' ') AS cleaned_name
    FROM unnested
    WHERE lower(name_part) NOT IN ('supergroup', 'group', 'subgroup', 'formation', 'member', 'bed', 'beds', 'and', 'upper', 'middle', 'lower') AND
        lower(name_part) NOT IN (
            SELECT lower(lith)
            FROM macrostrat.liths
            UNION ALL
            SELECT lower(concat(lith, 's'))
            FROM macrostrat.liths
        )
    GROUP BY collection_no
)
UPDATE macrostrat.pbdb_collections_new SET formation_clean = cleaned_name
FROM cleaned
WHERE cleaned.collection_no = pbdb_collections_new.collection_no;

WITH clean AS (
    SELECT collection_no, lower(regexp_replace(regexp_replace(replace(replace(member, '.', ''), '"', ''), '\(\.*\)', ''), '\s+$', '')) AS name
    FROM macrostrat.pbdb_collections_new
),
unnested AS (
    SELECT collection_no, a.name_part, a.nr
    FROM clean
    LEFT JOIN LATERAL unnest(string_to_array(name, ' '))
    WITH ORDINALITY AS a(name_part, nr) ON TRUE
),
cleaned AS (
    SELECT collection_no, array_to_string(array_agg(name_part), ' ') AS cleaned_name
    FROM unnested
    WHERE lower(name_part) NOT IN ('supergroup', 'group', 'subgroup', 'formation', 'member', 'bed', 'beds', 'and', 'upper', 'middle', 'lower') AND
        lower(name_part) NOT IN (
            SELECT lower(lith)
            FROM macrostrat.liths
            UNION ALL
            SELECT lower(concat(lith, 's'))
            FROM macrostrat.liths
        )
    GROUP BY collection_no
)
UPDATE macrostrat.pbdb_collections_new SET member_clean = cleaned_name
FROM cleaned
WHERE cleaned.collection_no = pbdb_collections_new.collection_no;

UPDATE macrostrat.pbdb_collections_new SET grp = NULL WHERE grp = '';
UPDATE macrostrat.pbdb_collections_new SET grp_clean = NULL WHERE grp_clean = '';
UPDATE macrostrat.pbdb_collections_new SET formation = NULL WHERE formation = '';
UPDATE macrostrat.pbdb_collections_new SET formation_clean = NULL WHERE formation_clean = '';
UPDATE macrostrat.pbdb_collections_new SET member = NULL WHERE member = '';
UPDATE macrostrat.pbdb_collections_new SET member_clean = NULL WHERE member_clean = '';

