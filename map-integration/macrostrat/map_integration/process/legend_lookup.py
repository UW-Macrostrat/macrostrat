import random
import sys

import spectra
from psycopg2.extensions import AsIs

from ..database import LegacyCommandBase
from ..utils import MapInfo


def legend_lookup(source: MapInfo):
    """
    Refresh the appropriate lookup tables for a given map source
    """
    LegendLookup().run(source.id)


class LegendLookup(LegacyCommandBase):

    scaleIsIn = {
        "tiny": ["tiny", "small"],
        "small": ["small", "medium"],
        "medium": ["medium", "large"],
        "large": ["large"],
    }

    def run(self, source_id):
        self.pg["cursor"].execute(
            """
            SELECT scale
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """,
            {"source_id": source_id},
        )
        scale = self.pg["cursor"].fetchone()

        print("Starting to process source %s" % (source_id,))

        if scale is None:
            print("Source ID %s was not found in maps.sources" % (source_id,))
            sys.exit(1)

        if scale[0] is None:
            print("Source ID %s is missing a scale" % (source_id,))
            sys.exit(1)

        scale = scale[0]

        self.pg["cursor"].execute(
            """
            -- Find unique match types for units
           WITH unit_bases AS (
             SELECT legend_id, array_agg(distinct basis_col) bases
             FROM maps.map_units
             JOIN maps.%(scale)s q ON map_units.map_id = q.map_id
             JOIN maps.map_legend ON map_legend.map_id = q.map_id
             WHERE source_id = %(source_id)s
             GROUP BY legend_id
             ORDER BY legend_id
           ),

           -- Find and aggregate best unit_ids for each map_id
           units AS (
             SELECT map_legend.legend_id, array_agg(DISTINCT unit_id) AS unit_ids
             FROM maps.map_units
             JOIN maps.%(scale)s q ON map_units.map_id = q.map_id
             JOIN maps.map_legend ON map_legend.map_id = q.map_id
             JOIN unit_bases ON unit_bases.legend_id = map_legend.legend_id
             WHERE source_id = %(source_id)s AND map_units.basis_col = ANY(
               CASE
                 WHEN 'manual' = ANY(bases)
                   THEN array['manual']

                 WHEN 'strat_name' = ANY(bases)
                  THEN array['strat_name', 'manual']

                 WHEN 'strat_name_fname' = ANY(bases)
                   THEN array['strat_name_fname', 'manual']

                 WHEN 'strat_name_fspace' = ANY(bases)
                   THEN array['strat_name_fspace', 'manual']

                 WHEN 'strat_name_ftime' = ANY(bases)
                   THEN array['strat_name_ftime', 'manual']

                 WHEN 'strat_name_fname_fspace' = ANY(bases)
                    THEN array['strat_name_fname_fspace', 'manual']

                 WHEN 'strat_name_fspace_ftime' = ANY(bases)
                    THEN array['strat_name_fspace_ftime', 'manual']

                 WHEN 'strat_name_fname_ftime' = ANY(bases)
                    THEN array['strat_name_fname_ftime', 'manual']

                 WHEN 'strat_name_fname_fspace_ftime' = ANY(bases)
                    THEN array['strat_name_fname_fspace_ftime', 'manual']

      --------------------------------------------------------------------------------------------
                 WHEN 'name' = ANY(bases)
                  THEN array['name', 'manual']

                 WHEN 'name_fname' = ANY(bases)
                  THEN array['name_fname', 'manual']

                 WHEN 'name_fspace' = ANY(bases)
                  THEN array['name_fspace', 'manual']

                 WHEN 'name_ftime' = ANY(bases)
                  THEN array['name_ftime', 'manual']

                 WHEN 'name_fname_fspace' = ANY(bases)
                   THEN array['name_fname_fspace', 'manual']

                 WHEN 'name_fspace_ftime' = ANY(bases)
                   THEN array['name_fspace_ftime', 'manual']

                 WHEN 'name_fname_ftime' = ANY(bases)
                   THEN array['name_fname_ftime', 'manual']

                 WHEN 'name_fname_fspace_ftime' = ANY(bases)
                   THEN array['name_fname_fspace_ftime', 'manual']

      --------------------------------------------------------------------------------------------
                 WHEN ('descrip' = ANY(bases) OR 'comments' = ANY(bases))
                  THEN array['descrip', 'comments', 'manual']

                 WHEN ('descrip_fname' = ANY(bases) OR 'comments_fname' = ANY(bases))
                  THEN array['descrip_fname', 'comments_fname', 'manual']

                 WHEN ('descrip_fspace' = ANY(bases) OR 'comments_fspace' = ANY(bases))
                  THEN array['descrip_fspace', 'comments_fspace', 'manual']

                 WHEN ('descrip_ftime' = ANY(bases) OR 'comments_ftime' = ANY(bases))
                  THEN array['descrip_ftime', 'comments_ftime', 'manual']

                 WHEN ('descrip_fname_fspace' = ANY(bases) OR 'comments_fname_fspace' = ANY(bases))
                   THEN array['descrip_fname_fspace', 'comments_fname_fspace', 'manual']

                 WHEN ('descrip_fspace_ftime' = ANY(bases) OR 'comments_fspace_ftime' = ANY(bases))
                   THEN array['descrip_fspace_ftime', 'comments_fspace_ftime', 'manual']

                 WHEN ('descrip_fname_ftime' = ANY(bases) OR 'comments_fname_ftime' = ANY(bases))
                   THEN array['descrip_fname_ftime', 'comments_fname_ftime', 'manual']

                 WHEN ('descrip_fname_fspace_ftime' = ANY(bases) OR 'comments_fname_fspace_ftime' = ANY(bases))
                   THEN array['descrip_fname_fspace_ftime', 'comments_fname_fspace_ftime', 'manual']

                 ELSE
                  array['unknown', 'manual']
                 END
             )
             GROUP BY map_legend.legend_id
           )
           UPDATE maps.legend
           SET unit_ids = units.unit_ids
           FROM units
           WHERE units.legend_id = legend.legend_id;
        """,
            {"scale": AsIs(scale), "source_id": source_id},
        )
        self.pg["connection"].commit()

        print("Ran first command")

        self.pg["cursor"].execute(
            """
            -- Find unique match types of strat_names
            WITH strat_name_bases AS (
              SELECT legend_id, array_agg(distinct basis_col) bases
              FROM maps.map_strat_names
              JOIN maps.%(scale)s q ON map_strat_names.map_id = q.map_id
              JOIN maps.map_legend ON map_legend.map_id = q.map_id
              WHERE source_id = %(source_id)s
              GROUP BY legend_id
              ORDER BY legend_id
            ),

            -- Find and aggregate best strat_name_ids for each map_id
            strat_names AS (
              SELECT map_legend.legend_id, array_agg(DISTINCT strat_name_id) AS strat_name_ids
              FROM maps.map_strat_names
              JOIN maps.%(scale)s q ON map_strat_names.map_id = q.map_id
              JOIN maps.map_legend ON map_legend.map_id = q.map_id
              JOIN strat_name_bases ON strat_name_bases.legend_id = map_legend.legend_id
              WHERE source_id = %(source_id)s AND map_strat_names.basis_col = ANY(
                CASE
                  WHEN 'manual' = ANY(bases)
                    THEN array['manual']

                  WHEN 'strat_name' = ANY(bases)
                   THEN array['strat_name', 'manual']

                  WHEN 'strat_name_fspace' = ANY(bases)
                    THEN array['strat_name_fspace', 'manual']

                  WHEN 'strat_name_ftime' = ANY(bases)
                    THEN array['strat_name_ftime', 'manual']

                  WHEN 'strat_name_fspace_ftime' = ANY(bases)
                    THEN array['strat_name_fspace_ftime', 'manual']

                  WHEN 'strat_name_ntime' = ANY(bases)
                    THEN array['strat_name_ntime', 'manual']

                  WHEN 'strat_name_fspace_ntime' = ANY(bases)
                    THEN array['strat_name_fspace_ntime', 'manual']

                  WHEN 'strat_name_fname' = ANY(bases)
                    THEN array['strat_name_fname', 'manual']

                  WHEN 'strat_name_fname_fspace' = ANY(bases)
                     THEN array['strat_name_fname_fspace', 'manual']

                  WHEN 'strat_name_fname_ftime' = ANY(bases)
                     THEN array['strat_name_fname_ftime', 'manual']

                  WHEN 'strat_name_fname_fspace_ftime' = ANY(bases)
                     THEN array['strat_name_fname_fspace_ftime', 'manual']

                  WHEN 'strat_name_fname_ftime' = ANY(bases)
                     THEN array['strat_name_fname_ftime', 'manual']

                  WHEN 'strat_name_fname_fspace_ntime' = ANY(bases)
                     THEN array['strat_name_fname_fspace_ntime', 'manual']

       --------------------------------------------------------------------------------------------
                  WHEN 'name' = ANY(bases)
                   THEN array['name', 'manual']

                  WHEN 'name_fname' = ANY(bases)
                   THEN array['name_fname', 'manual']

                  WHEN 'name_fspace' = ANY(bases)
                   THEN array['name_fspace', 'manual']

                  WHEN 'name_ftime' = ANY(bases)
                   THEN array['name_ftime', 'manual']

                  WHEN 'name_fname_fspace' = ANY(bases)
                    THEN array['name_fname_fspace', 'manual']

                  WHEN 'name_fspace_ftime' = ANY(bases)
                    THEN array['name_fspace_ftime', 'manual']

                  WHEN 'name_fname_ftime' = ANY(bases)
                    THEN array['name_fname_ftime', 'manual']

                  WHEN 'name_fname_fspace_ftime' = ANY(bases)
                    THEN array['name_fname_fspace_ftime', 'manual']

       --------------------------------------------------------------------------------------------
                  WHEN ('descrip' = ANY(bases) OR 'comments' = ANY(bases))
                   THEN array['descrip', 'comments', 'manual']

                  WHEN ('descrip_fname' = ANY(bases) OR 'comments_fname' = ANY(bases))
                   THEN array['descrip_fname', 'comments_fname', 'manual']

                  WHEN ('descrip_fspace' = ANY(bases) OR 'comments_fspace' = ANY(bases))
                   THEN array['descrip_fspace', 'comments_fspace', 'manual']

                  WHEN ('descrip_ftime' = ANY(bases) OR 'comments_ftime' = ANY(bases))
                   THEN array['descrip_ftime', 'comments_ftime', 'manual']

                  WHEN ('descrip_fname_fspace' = ANY(bases) OR 'comments_fname_fspace' = ANY(bases))
                    THEN array['descrip_fname_fspace', 'comments_fname_fspace', 'manual']

                  WHEN ('descrip_fspace_ftime' = ANY(bases) OR 'comments_fspace_ftime' = ANY(bases))
                    THEN array['descrip_fspace_ftime', 'comments_fspace_ftime', 'manual']

                  WHEN ('descrip_fname_ftime' = ANY(bases) OR 'comments_fname_ftime' = ANY(bases))
                    THEN array['descrip_fname_ftime', 'comments_fname_ftime', 'manual']

                  WHEN ('descrip_fname_fspace_ftime' = ANY(bases) OR 'comments_fname_fspace_ftime' = ANY(bases))
                    THEN array['descrip_fname_fspace_ftime', 'comments_fname_fspace_ftime', 'manual']

                  ELSE
                   array['unknown', 'manual']
                  END
              )
              GROUP BY map_legend.legend_id
            )
            UPDATE maps.legend
            SET strat_name_ids = strat_names.strat_name_ids
            FROM strat_names
            WHERE strat_names.legend_id = legend.legend_id;
        """,
            {"scale": AsIs(scale), "source_id": source_id},
        )
        self.pg["connection"].commit()

        print("Ran second command")

        # Update specific liths
        self.pg["cursor"].execute(
            """
            WITH lith_bases AS (
              SELECT array_agg(distinct basis_col) bases, q.legend_id
              FROM maps.legend_liths
              JOIN maps.legend q ON legend_liths.legend_id = q.legend_id
              WHERE source_id = %(source_id)s
              GROUP BY q.legend_id
              ORDER BY q.legend_id
            ),
            liths AS (
               SELECT
                   map_legend.legend_id,
                   array_agg(DISTINCT lith_equiv) AS lith_ids,
                   array_agg(DISTINCT liths.lith_type) AS lith_types,
                   array_agg(DISTINCT liths.lith_class) AS lith_classes
               FROM (
                   SELECT legend_liths.legend_id, legend_liths.lith_id
                   FROM maps.legend_liths
                   JOIN maps.legend ON legend_liths.legend_id = legend.legend_id
                   JOIN lith_bases ON lith_bases.legend_id = legend.legend_id
                   WHERE source_id = %(source_id)s
                    AND legend_liths.basis_col =
                        CASE
                            WHEN 'lith' = ANY(bases)
                                THEN 'lith'
                            WHEN 'descrip' = ANY(bases)
                                THEN 'descrip'
                            WHEN 'name' = ANY(bases)
                                THEN 'name'
                            WHEN 'comments' = ANY(bases)
                                THEN 'comments'
                            ELSE ''
                        END
               ) sub
               JOIN maps.map_legend ON map_legend.legend_id = sub.legend_id
               JOIN macrostrat.liths ON sub.lith_id = liths.id
               GROUP BY map_legend.legend_id
            )
            UPDATE maps.legend
            SET lith_ids = liths.lith_ids, lith_types = liths.lith_types, lith_classes = liths.lith_classes
            FROM liths
            WHERE liths.legend_id = legend.legend_id;
        """,
            {"scale": AsIs(scale), "source_id": source_id},
        )
        self.pg["connection"].commit()

        print("Ran third command")

        # Update all liths
        self.pg["cursor"].execute(
            """
            UPDATE maps.legend
            SET
                all_lith_ids = sub.lith_ids,
                all_lith_types = sub.lith_types,
                all_lith_classes = sub.lith_classes
            FROM (
                SELECT
                    legend.legend_id,
                    array_agg(DISTINCT liths.lith_equiv) AS lith_ids,
                    array_agg(DISTINCT liths.lith_type) AS lith_types,
                    array_agg(DISTINCT liths.lith_class) AS lith_classes
                FROM maps.legend_liths
                JOIN maps.legend ON legend_liths.legend_id = legend.legend_id
                JOIN macrostrat.liths ON liths.id = legend_liths.lith_id
                WHERE legend.source_id = %(source_id)s
                GROUP BY legend.legend_id
            ) sub
            WHERE legend.legend_id = sub.legend_id;
        """,
            {"source_id": source_id},
        )
        self.pg["connection"].commit()

        print("Ran fourth command")

        # Update concept_ids and strat_name_children
        self.pg["cursor"].execute(
            """
            WITH more_strat_names AS (
                SELECT
                    sub.legend_id,
                    array((SELECT DISTINCT Unnest(array_cat(concept_ids, ac)))) as concept_ids,
                    (
                        SELECT array_agg(DISTINCT strat_name_id)
                        FROM macrostrat.lookup_strat_names
                        WHERE bed_id = ANY(strat_name_ids)
                            OR mbr_id = ANY(strat_name_ids)
                            OR fm_id = ANY(strat_name_ids)
                            OR gp_id = ANY(strat_name_ids)
                            OR sgp_id = ANY(strat_name_ids)
                    ) AS strat_name_children
                FROM (
                    SELECT
                     map_legend.legend_id,
                     legend.strat_name_ids,
                     array_agg(DISTINCT applicable_concepts.applicable_concepts) as ac,
                     array_agg(DISTINCT lsn.concept_id) AS concept_ids
                    FROM maps.legend
                    JOIN maps.map_legend ON map_legend.legend_id = legend.legend_id
                    JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = ANY(legend.strat_name_ids)
                    JOIN (
                        SELECT
                            ids.strat_name_id,
                            unnest((
                                SELECT COALESCE(array_agg(id), ARRAY[]::int[])
                                FROM unnest(array_agg(ARRAY[lookup_bed.concept_id, lookup_mbr.concept_id, lookup_fm.concept_id, lookup_gp.concept_id, lookup_sgp.concept_id])) as id
                                WHERE id is not null and id != 0
                             )) as applicable_concepts
                        FROM (
                          SELECT
                            strat_name_id,
                            CASE
                                WHEN bed_id = 0
                                    THEN NULL
                                ELSE bed_id
                            END as bed_id,
                            CASE
                                WHEN mbr_id = 0
                                    THEN NULL
                                ELSE mbr_id
                            END as mbr_id,
                            CASE
                                WHEN fm_id = 0
                                    THEN NULL
                                ELSE fm_id
                            END as fm_id,
                            CASE
                                WHEN gp_id = 0
                                    THEN NULL
                                ELSE gp_id
                            END as gp_id,
                            CASE
                                WHEN sgp_id = 0
                                    THEN NULL
                                ELSE sgp_id
                            END as sgp_id
                        FROM macrostrat.lookup_strat_names
                        ) ids
                        LEFT JOIN macrostrat.lookup_strat_names lookup_bed ON lookup_bed.strat_name_id = ids.bed_id
                        LEFT JOIN macrostrat.lookup_strat_names lookup_mbr ON lookup_mbr.strat_name_id = ids.mbr_id
                        LEFT JOIN macrostrat.lookup_strat_names lookup_fm ON lookup_fm.strat_name_id = ids.fm_id
                        LEFT JOIN macrostrat.lookup_strat_names lookup_gp ON lookup_gp.strat_name_id = ids.gp_id
                        LEFT JOIN macrostrat.lookup_strat_names lookup_sgp ON lookup_sgp.strat_name_id = ids.sgp_id
                        GROUP BY ids.strat_name_id
                    ) applicable_concepts ON applicable_concepts.strat_name_id = lsn.strat_name_id
                    WHERE legend.source_id = %(source_id)s
                    GROUP BY map_legend.legend_id, legend.strat_name_ids
                ) sub
             )
            UPDATE maps.legend
            SET concept_ids =
            CASE
                WHEN array_length(legend.unit_ids, 1) = 0 OR legend.unit_ids is null
                    THEN COALESCE(more_strat_names.concept_ids, '{}')
                ELSE
                    (
                        SELECT array((SELECT DISTINCT unnest(array_cat(COALESCE(more_strat_names.concept_ids, '{}'), array_agg(DISTINCT lsn.concept_id)))))
                        FROM macrostrat.unit_strat_names usn
                        JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = usn.strat_name_id
                        WHERE usn.unit_id = ANY(legend.unit_ids)
                    )
                END,
                strat_name_children = COALESCE(more_strat_names.strat_name_children, '{}')
            FROM more_strat_names
            WHERE more_strat_names.legend_id = legend.legend_id;
        """,
            {"scale": AsIs(scale), "source_id": source_id},
        )
        self.pg["connection"].commit()

        print("Ran fifth command")

        # Update best_age_top and best_age_bottom and color
        self.pg["cursor"].execute(
            """
            WITH ages AS (
                SELECT
                 legend_id,
                 CASE
                    WHEN
                        (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) IS NULL
                    THEN ti.age_top
                    ELSE (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids))
                 END best_age_top,
                 CASE
                    WHEN
                        (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) IS NULL
                    THEN tb.age_bottom
                    ELSE (SELECT max(b_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids))
                 END as best_age_bottom
               FROM maps.legend
               LEFT JOIN macrostrat.intervals ti ON ti.id = t_interval
               LEFT JOIN macrostrat.intervals tb ON tb.id = b_interval
               WHERE legend.source_id = %(source_id)s
            )

            UPDATE maps.legend
            SET best_age_top = ages.best_age_top, best_age_bottom = ages.best_age_bottom,
            color = CASE
              WHEN name ilike 'water'
                  THEN ''
              ELSE
                (SELECT interval_color
                 FROM macrostrat.intervals
                 WHERE age_top <= ages.best_age_top AND age_bottom >= ages.best_age_bottom
                 -- Exclude New Zealand ages as possible matches
                 AND intervals.id NOT IN (SELECT interval_id FROM macrostrat.timescales_intervals WHERE timescale_id = 6)
                 ORDER BY age_bottom - age_top
                 LIMIT 1
                )
              END
            FROM ages
            WHERE ages.legend_id = legend.legend_id;
        """,
            {"scale": AsIs(scale), "source_id": source_id},
        )
        self.pg["connection"].commit()

        print("Ran sixth command")

        # Shift colors where needed
        self.pg["cursor"].execute(
            """
            SELECT color, c, legend_ids, best_age_bottom, best_age_top
            FROM (
                select color, count(*) c, array_agg(legend_id) AS legend_ids, best_age_bottom, best_age_top
                FROM maps.legend
                WHERE source_id = %(source_id)s
                GROUP BY color, best_age_bottom, best_age_top
            ) sub
            WHERE c > 1;
        """,
            {"source_id": source_id},
        )
        colors = self.pg["cursor"].fetchall()

        print("Ran seventh command")

        for color in colors:
            if color.color is None:
                continue
            try:
                c = spectra.html(color.color)
            except:
                print(color)
                continue

            variants = [
                c.brighten(amount=3).hexcode,
                c.darken(amount=3).hexcode,
                c.brighten(amount=6).hexcode,
                c.darken(amount=6).hexcode,
                c.brighten(amount=9).hexcode,
                c.darken(amount=9).hexcode,
                c.saturate(amount=10).hexcode,
                c.desaturate(amount=10).hexcode,
                c.desaturate(amount=20).hexcode,
                c.saturate(amount=20).hexcode,
                c.saturate(amount=30).hexcode,
            ]
            used_variants = []

            for idx, legend_id in enumerate(color.legend_ids):
                # allow one to maintain its original color
                if idx == 0:
                    continue
                # If we have used all the colors start over
                if len(used_variants) == len(variants):
                    used_variants = []

                valid_choice = False
                loops = 0
                while not valid_choice:
                    new_color = random.choice(variants)
                    loops = loops + 1
                    if new_color not in used_variants:
                        valid_choice = True
                        used_variants.append(new_color)
                    elif loops > len(variants):
                        used_variants = []

                self.pg["cursor"].execute(
                    """
                    UPDATE maps.legend
                    SET color = %(color)s
                    WHERE legend_id = %(legend_id)s
                """,
                    {"color": new_color, "legend_id": legend_id},
                )

            self.pg["connection"].commit()

        print("Ran eighth command")

        # Now go back and homogenize similar units
        self.pg["cursor"].execute(
            """
            WITH first AS (
                SELECT DISTINCT ON (legend.name, b_interval, t_interval) legend.name, b_interval, t_interval, count(distinct legend_id), array_agg(distinct legend_id) AS legend_ids, array_agg(distinct color) AS colors
                FROM maps.legend
                JOIN maps.sources on legend.source_id = legend.source_id
                WHERE scale = ANY(%(scales)s)
                GROUP BY legend.name, b_interval, t_interval
            )
            SELECT legend_ids, colors
            FROM first
            WHERE array_length(legend_ids, 1) > 1;
        """,
            {"scales": LegendLookup.scaleIsIn[scale]},
        )
        similar_units = self.pg["cursor"].fetchall()

        print("Ran ninth command")

        for idx, unit in enumerate(similar_units):
            # print '%s of %s' % (idx, len(similar_units), )
            # Just pick the first color
            color = unit.colors[0]

            print(unit.legend_ids)

            self.pg["cursor"].execute(
                """
                UPDATE maps.legend
                SET color = %(color)s
                WHERE legend_id = ANY(%(legend_id)s)
            """,
                {"color": color, "legend_id": unit.legend_ids},
            )
            self.pg["connection"].commit()

        print("Done")
