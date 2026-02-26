SET search_path TO macrostrat, public;
DROP TABLE IF EXISTS macrostrat.strat_name_footprints_old;
DROP TABLE IF EXISTS macrostrat.strat_name_footprints_new;

CREATE TABLE macrostrat.strat_name_footprints_new AS
    WITH first as (
      SELECT
        DISTINCT lsn.strat_name_id,
        lsn.name_no_lith,
        lsn.rank_name,
        lsn.concept_id,
        array(
          SELECT DISTINCT strat_name_id
          FROM macrostrat.lookup_strat_names
          WHERE lookup_strat_names.bed_id = lsn.strat_name_id
            OR lookup_strat_names.mbr_id = lsn.strat_name_id
            OR lookup_strat_names.fm_id = lsn.strat_name_id
            OR lookup_strat_names.gp_id = lsn.strat_name_id
            OR lookup_strat_names.sgp_id = lsn.strat_name_id
        ) AS names_in_hierarchy
      FROM macrostrat.lookup_strat_names lsn
      GROUP BY lsn.strat_name_id, lsn.concept_id, lsn.name_no_lith, lsn.rank_name
    ),
    second AS (
      SELECT concept_id, array_agg(DISTINCT i) concept_names
      FROM (
        SELECT concept_id, unnest(names_in_hierarchy) i
        FROM first
      ) foo
      WHERE concept_id != 0
      GROUP BY concept_id
    )
    SELECT strat_name_id, name_no_lith, rank_name, second.concept_id, second.concept_names, ST_Union(ARRAY[(
      SELECT COALESCE(ST_Union(ST_MakeValid(poly_geom)), 'SRID=4326;POLYGON EMPTY') AS geom
      FROM macrostrat.unit_strat_names
      JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
      JOIN macrostrat.cols ON units_sections.col_id = cols.id
      WHERE unit_strat_names.strat_name_id = ANY(second.concept_names)
    ), (
      SELECT COALESCE(ST_Union(ST_MakeValid(geom)), 'SRID=4326;POLYGON EMPTY') as geom
      FROM macrostrat.strat_names_places
      JOIN macrostrat.places ON places.place_id = strat_names_places.place_id
      WHERE strat_names_places.strat_name_id = ANY(second.concept_names)
    ),(
        SELECT COALESCE(ST_MakeValid(ST_Envelope(ST_Collect(ST_SetSRID(ST_MakeValid(poly_geom), 4326)))), 'SRID=4326;POLYGON EMPTY') AS geom
        FROM macrostrat.cols
        JOIN macrostrat.units_sections us ON us.col_id = cols.id
        JOIN macrostrat.unit_strat_names usn ON usn.unit_id = us.unit_id
        WHERE usn.strat_name_id = ANY(first.names_in_hierarchy)
    )]) AS geom,
    LEAST((
      SELECT min(t_age)
      FROM macrostrat.lookup_unit_intervals
      JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
      JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
      JOIN macrostrat.cols ON units_sections.col_id = cols.id
      WHERE unit_strat_names.strat_name_id = ANY(second.concept_names) OR unit_strat_names.strat_name_id = ANY(first.names_in_hierarchy)
    ),ti.age_top) AS best_t_age,
    GREATEST((
      SELECT max(b_age)
      FROM macrostrat.lookup_unit_intervals
      JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
      JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
      JOIN macrostrat.cols ON units_sections.col_id = cols.id
      WHERE unit_strat_names.strat_name_id = ANY(second.concept_names) OR unit_strat_names.strat_name_id = ANY(first.names_in_hierarchy)
    ), tb.age_bottom) AS best_b_age
FROM first
LEFT JOIN second ON first.concept_id = second.concept_id
LEFT JOIN macrostrat.strat_names_meta ON second.concept_id = strat_names_meta.concept_id
LEFT JOIN macrostrat.intervals ti ON strat_names_meta.t_int = ti.id
LEFT JOIN macrostrat.intervals tb ON strat_names_meta.b_int = tb.id
;

UPDATE macrostrat.strat_name_footprints_new SET geom = 'POLYGON EMPTY' WHERE ST_GeometryType(geom) = 'ST_Point';

INSERT INTO macrostrat.strat_name_footprints_new
WITH first as (
  SELECT
    DISTINCT lsn.strat_name_id,
    lsn.name_no_lith,
    lsn.rank_name,
    lsn.concept_id,
    array(
      SELECT DISTINCT strat_name_id
      FROM macrostrat.lookup_strat_names
      WHERE lookup_strat_names.bed_id = lsn.strat_name_id
        OR lookup_strat_names.mbr_id = lsn.strat_name_id
        OR lookup_strat_names.fm_id = lsn.strat_name_id
        OR lookup_strat_names.gp_id = lsn.strat_name_id
        OR lookup_strat_names.sgp_id = lsn.strat_name_id
    ) AS names_in_hierarchy
  FROM macrostrat.lookup_strat_names lsn
  WHERE lsn.strat_name_id NOT IN (
    SELECT DISTINCT strat_name_id
    FROM macrostrat.strat_name_footprints_new
    WHERE ST_AsText(geom) = 'POLYGON EMPTY'
    AND concept_id = 0
  )
  GROUP BY lsn.strat_name_id, lsn.concept_id, lsn.name_no_lith, lsn.rank_name
),
third AS (
  SELECT strat_name_id, 0 AS concept_id, names_in_hierarchy AS concept_names
  FROM first
  WHERE concept_id = 0
)
SELECT third.strat_name_id, name_no_lith, rank_name, third.concept_id, third.concept_names, ST_Union(ARRAY[(
  SELECT COALESCE(ST_MakeValid(ST_Union(ST_MakeValid(poly_geom))), 'SRID=4326;POLYGON EMPTY') AS geom
  FROM macrostrat.unit_strat_names
  JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
  JOIN macrostrat.cols ON units_sections.col_id = cols.id
  WHERE unit_strat_names.strat_name_id = ANY(third.concept_names)
), (
  SELECT COALESCE(ST_MakeValid(ST_Union(ST_MakeValid(geom))), 'SRID=4326;POLYGON EMPTY') as geom
  FROM macrostrat.strat_names_places
  JOIN macrostrat.places ON places.place_id = strat_names_places.place_id
  WHERE strat_names_places.strat_name_id = ANY(third.concept_names)
),(
    SELECT COALESCE(ST_MakeValid(ST_Envelope(ST_Collect(ST_SetSRID(ST_MakeValid(poly_geom), 4326)))), 'SRID=4326;POLYGON EMPTY') AS geom
    FROM macrostrat.cols
    JOIN macrostrat.units_sections us ON us.col_id = cols.id
    JOIN macrostrat.unit_strat_names usn ON usn.unit_id = us.unit_id
    WHERE usn.strat_name_id = ANY(third.concept_names)
)]) AS geom,
LEAST((
  SELECT min(t_age)
  FROM macrostrat.lookup_unit_intervals
  JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
  JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
  JOIN macrostrat.cols ON units_sections.col_id = cols.id
  WHERE unit_strat_names.strat_name_id = ANY(third.concept_names)
),ti.age_top) AS best_t_age,
GREATEST((
  SELECT max(b_age)
  FROM macrostrat.lookup_unit_intervals
  JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
  JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
  JOIN macrostrat.cols ON units_sections.col_id = cols.id
  WHERE unit_strat_names.strat_name_id = ANY(third.concept_names)
), tb.age_bottom) AS best_b_age
FROM third
LEFT JOIN macrostrat.strat_names_meta ON third.concept_id = strat_names_meta.concept_id
JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = third.strat_name_id
LEFT JOIN macrostrat.intervals ti ON strat_names_meta.t_int = ti.id
LEFT JOIN macrostrat.intervals tb ON strat_names_meta.b_int = tb.id
;

UPDATE macrostrat.strat_name_footprints_new SET geom = 'POLYGON EMPTY' WHERE ST_GeometryType(geom) = 'ST_Point';
UPDATE macrostrat.strat_name_footprints_new SET geom = ST_SetSRID(geom, 4326);

UPDATE macrostrat.strat_name_footprints_new
SET geom = st_collectionextract(geom, 3)
WHERE st_geometrytype(geom) = 'ST_GeometryCollection';

CREATE INDEX ON macrostrat.strat_name_footprints_new (strat_name_id);
CREATE INDEX ON macrostrat.strat_name_footprints_new USING GiST (geom);



ALTER TABLE IF EXISTS macrostrat.strat_name_footprints RENAME TO strat_name_footprints_old;
ALTER TABLE macrostrat.strat_name_footprints_new RENAME to strat_name_footprints;
