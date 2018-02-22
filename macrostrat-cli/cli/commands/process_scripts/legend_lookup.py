from ..base import Base
from psycopg2.extensions import AsIs
import sys
import spectra
import random

class LegendLookup(Base):
    """
    macrostrat process legend_lookup <source_id>:
        Updates the computed fields in maps.legend for a given source

    Usage:
      macrostrat process legend_lookup <source_id>
      macrostrat process legend_lookup -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat process legend_lookup 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Refresh the appropriate lookup tables for a given map source
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }
    scaleIsIn = {
        'tiny': ['tiny', 'small'],
        'small': ['small', 'medium'],
        'medium': ['medium', 'large'],
        'large': ['large']
    }

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)


    def run(self, source_id):
        if len(source_id) == 0 or source_id[0] == '--help' or source_id[0] == '-h':
            print LegendLookup.__doc__
            sys.exit()

        source_id = source_id[0]

        self.pg['cursor'].execute('''
            SELECT scale
            FROM maps.sources
            WHERE source_id = %(source_id)s
        ''', { 'source_id': source_id })
        scale = self.pg['cursor'].fetchone()

        if scale is None:
            print 'Source ID %s was not found in maps.sources' % (source_id, )
            sys.exit(1)

        if scale[0] is None:
            print 'Source ID %s is missing a scale' % (source_id, )
            sys.exit(1)

        scale = scale[0]

        self.pg['cursor'].execute("""
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
        """, {
           'scale': AsIs(scale),
           'source_id': source_id
        })
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
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
            SET strat_name_ids =
            CASE
                WHEN array_length(legend.unit_ids, 1) = 0
                    THEN strat_names.strat_name_ids
                ELSE
                    (
                        SELECT array_agg(DISTINCT lsn.strat_name_id)
                        FROM macrostrat.unit_strat_names usn
                        JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = usn.strat_name_id
                        WHERE usn.unit_id = ANY(legend.unit_ids)
                    )
                END
            FROM strat_names
            WHERE strat_names.legend_id = legend.legend_id;
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
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
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
            WITH more_strat_names AS (
                SELECT
                    sub.legend_id,
                    concept_ids,
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
                     array_agg(DISTINCT lsn.concept_id) AS concept_ids
                    FROM maps.%(scale)s q
                    JOIN maps.map_legend ON map_legend.map_id = q.map_id
                    JOIN maps.legend ON legend.legend_id = map_legend.legend_id
                    JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = ANY(legend.strat_name_ids)
                    WHERE q.source_id = %(source_id)s
                    GROUP BY map_legend.legend_id, legend.strat_name_ids
                ) sub
             )
            UPDATE maps.legend
            SET concept_ids =
            CASE
                WHEN array_length(legend.unit_ids, 1) = 0
                    THEN COALESCE(more_strat_names.concept_ids, '{}')
                ELSE
                    (
                        SELECT array_agg(DISTINCT lsn.concept_id)
                        FROM macrostrat.unit_strat_names usn
                        JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = usn.strat_name_id
                        WHERE usn.unit_id = ANY(legend.unit_ids)
                    )
                END,
                strat_name_children = COALESCE(more_strat_names.strat_name_children, '{}')
            FROM more_strat_names
            WHERE more_strat_names.legend_id = legend.legend_id;
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
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
                    ELSE (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids))
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
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()

        # Shift colors where needed
        self.pg['cursor'].execute("""
            SELECT color, c, legend_ids, best_age_bottom, best_age_top
            FROM (
                select color, count(*) c, array_agg(legend_id) AS legend_ids, best_age_bottom, best_age_top
                FROM maps.legend
                WHERE source_id = %(source_id)s
                GROUP BY color, best_age_bottom, best_age_top
            ) sub
            WHERE c > 1;
        """, { 'source_id': source_id })
        colors = self.pg['cursor'].fetchall()

        for color in colors:
            if color.color is None:
                continue
            try:
                c = spectra.html(color.color)
            except:
                print color
                continue

            variants = [
                c.brighten(amount=3).hexcode,
                c.brighten(amount=6).hexcode,
                c.brighten(amount=9).hexcode,
                c.darken(amount=3).hexcode,
                c.darken(amount=6).hexcode,
                c.darken(amount=9).hexcode,
                c.saturate(amount=10).hexcode,
                c.saturate(amount=20).hexcode,
                c.saturate(amount=30).hexcode,
                c.saturate(amount=40).hexcode,
                c.desaturate(amount=10).hexcode,
                c.desaturate(amount=20).hexcode
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
                    elif loops > 12:
                        used_variants = []


                self.pg['cursor'].execute("""
                    UPDATE maps.legend
                    SET color = %(color)s
                    WHERE legend_id = %(legend_id)s
                """, {
                    'color': new_color,
                    'legend_id': legend_id
                })

            self.pg['connection'].commit()

            # Now go back and homogenize similar units
            self.pg['cursor'].execute("""
                WITH first AS (
                    SELECT array_agg(legend_id) AS legend_ids, l.name, l.strat_name, l.age, array_agg(DISTINCT color) AS colors
                    FROM maps.legend l
                    JOIN (
                        SELECT DISTINCT ON (legend.name, b_interval, t_interval) legend.name, b_interval, t_interval
                        FROM maps.legend
                        JOIN maps.sources on legend.source_id = legend.source_id
                        where scale = ANY(%(scales)s)
                    ) sub ON sub.name = l.name AND sub.b_interval = l.b_interval AND sub.t_interval = l.t_interval
                    GROUP BY l.name, l.strat_name, l.age
                )
                SELECT legend_ids, colors
                FROM first
                WHERE array_length(legend_ids, 1) > 1;
            """, { 'scales': LegendLookup.scaleIsIn[scale] })
            similar_units = self.pg['cursor'].fetchall()

            for unit in similar_units:
                print unit
                # Just pick the first color
                color = unit.colors[0]

                for idx, legend_id in enumerate(unit.legend_ids):
                    # allow one to maintain its original color
                    if idx == 0:
                        continue

                    self.pg['cursor'].execute("""
                        UPDATE maps.legend
                        SET color = %(color)s
                        WHERE legend_id = %(legend_id)s
                    """, {
                        'color': color,
                        'legend_id': legend_id
                    })
                self.pg['connection'].commit()
