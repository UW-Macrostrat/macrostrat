from psycopg2.sql import Identifier

from macrostrat.core.exc import MacrostratError

from ..database import get_database
from ..utils import MapInfo
from ..utils.legend_color import LegendRow, assign_colors


def legend_lookup(source: MapInfo):
    """
    Refresh the appropriate lookup tables for a given map source
    """
    LegendLookup(get_database()).run(source.id)


class LegendLookup:
    def __init__(self, db):
        self.db = db

    def run(self, source_id):
        row = self.db.run_query(
            """
            SELECT scale
            FROM maps.sources
            WHERE source_id = :source_id
        """,
            {"source_id": source_id},
        ).first()

        print("Starting to process source %s" % (source_id,))

        # Raised rather than `sys.exit(1)`: these steps run over a selector now,
        # and exiting the process would abandon every map after this one.
        if row is None:
            raise MacrostratError(f"Source {source_id} was not found in maps.sources")
        if row.scale is None:
            raise MacrostratError(f"Source {source_id} is missing a scale")

        scale = row.scale

        self.db.run_sql(
            """
            -- Find unique match types for units
           WITH unit_bases AS (
             SELECT legend_id, array_agg(distinct basis_col) bases
             FROM maps.map_units
             JOIN {scale_table} q ON map_units.map_id = q.map_id
             JOIN maps.map_legend ON map_legend.map_id = q.map_id
             WHERE source_id = :source_id
             GROUP BY legend_id
             ORDER BY legend_id
           ),

           -- Find and aggregate best unit_ids for each map_id
           units AS (
             SELECT map_legend.legend_id, array_agg(DISTINCT unit_id) AS unit_ids
             FROM maps.map_units
             JOIN {scale_table} q ON map_units.map_id = q.map_id
             JOIN maps.map_legend ON map_legend.map_id = q.map_id
             JOIN unit_bases ON unit_bases.legend_id = map_legend.legend_id
             WHERE source_id = :source_id AND map_units.basis_col = ANY(
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
            {
                "scale_table": Identifier("maps", scale),
                "source_id": source_id,
            },
        )

        print("Ran first command")

        self.db.run_sql(
            """
            /* Keep each legend entry's strongest matches and drop the rest.

               `rank()` returns every match that ties at the top, which is what
               the `basis_col` ladder did by picking one tier and taking all of
               it -- but read off the evidence columns rather than reassembled
               from a string. */
            WITH ranked AS (
              SELECT
                lsn.legend_id,
                lsn.strat_name_id,
                rank() OVER (
                  PARTITION BY lsn.legend_id
          /* Strongest evidence first. A human assertion outranks everything;
             then the field the name was found in -- `strat_name` and `name` are
             the unit, a description is a mention; then temporal corroboration,
             then spatial. Description and comments share a rank, as the ladder
             this replaces also had them.

             This is the same order the forty `WHEN` branches expressed, including
             the part that reads oddly: a buffered footprint demotes *less* than
             fuzzed time, so `_fspace` sorted above `_ftime`. */
          ORDER BY
            lsn.is_manual DESC,
            CASE lsn.match_field
              WHEN 'strat_name' THEN 0
              WHEN 'name' THEN 1
              ELSE 2
            END,
            CASE
              WHEN lsn.age_overlaps THEN 0
              WHEN NOT lsn.age_overlaps THEN 1
              ELSE 2
            END,
            lsn.location_basis
                ) AS tier
              FROM maps.legend_strat_names lsn
              JOIN maps.legend l ON l.legend_id = lsn.legend_id
              WHERE l.source_id = :source_id
            ),
            strat_names AS (
              SELECT legend_id, array_agg(DISTINCT strat_name_id) AS strat_name_ids
              FROM ranked WHERE tier = 1
              GROUP BY legend_id
            )
            UPDATE maps.legend
            SET strat_name_ids = strat_names.strat_name_ids
            FROM strat_names
            WHERE strat_names.legend_id = legend.legend_id;
        """,
            {
                "scale_table": Identifier("maps", scale),
                "source_id": source_id,
            },
        )

        print("Ran second command")

        # Update specific liths
        self.db.run_sql(
            """
            WITH lith_bases AS (
              SELECT array_agg(distinct basis_col) bases, q.legend_id
              FROM maps.legend_liths
              JOIN maps.legend q ON legend_liths.legend_id = q.legend_id
              WHERE source_id = :source_id
              GROUP BY q.legend_id
              ORDER BY q.legend_id
            ),
            liths AS (
               /* `maps.map_legend` used to be joined here and contributed no
                  column: it multiplied each legend entry by its polygon count --
                  about 24x on a map the size of Alaska -- and the GROUP BY then
                  collapsed it again. The `lith_ids` CTE below does the same
                  aggregation without it. */
               SELECT
                   sub.legend_id,
                   array_agg(DISTINCT lith_equiv) AS lith_ids,
                   array_agg(DISTINCT liths.lith_type) AS lith_types,
                   array_agg(DISTINCT liths.lith_class) AS lith_classes
               FROM (
                   SELECT legend_liths.legend_id, legend_liths.lith_id
                   FROM maps.legend_liths
                   JOIN maps.legend ON legend_liths.legend_id = legend.legend_id
                   JOIN lith_bases ON lith_bases.legend_id = legend.legend_id
                   WHERE source_id = :source_id
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
               JOIN macrostrat.liths ON sub.lith_id = liths.id
               GROUP BY sub.legend_id
            )
            UPDATE maps.legend
            SET lith_ids = liths.lith_ids, lith_types = liths.lith_types, lith_classes = liths.lith_classes
            FROM liths
            WHERE liths.legend_id = legend.legend_id;
        """,
            {
                "scale_table": Identifier("maps", scale),
                "source_id": source_id,
            },
        )

        print("Ran third command")

        # Update all liths
        self.db.run_sql(
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
                WHERE legend.source_id = :source_id
                GROUP BY legend.legend_id
            ) sub
            WHERE legend.legend_id = sub.legend_id;
        """,
            {"source_id": source_id},
        )

        print("Ran fourth command")

        # Update concept_ids and strat_name_children
        self.db.run_sql(
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
                    /* Per legend entry, not per polygon. `maps.map_legend` was
                       joined here for a `legend_id` that `maps.legend` already
                       has, fanning every row out across the entry's polygons
                       before the GROUP BY put it back. */
                    SELECT
                     legend.legend_id,
                     legend.strat_name_ids,
                     coalesce(array_agg(DISTINCT anc.id)
                              FILTER (WHERE anc.id IS NOT NULL), '{{}}') as ac,
                     array_agg(DISTINCT lsn.concept_id) AS concept_ids
                    FROM maps.legend
                    JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = ANY(legend.strat_name_ids)
                    /* The ancestors' concepts come from the flattened rank
                       tree, which the lexicon rebuild maintains. This was a
                       five-way self-join over the whole of
                       `lookup_strat_names`, with no source predicate, rebuilt on
                       every run of every source. */
                    JOIN macrostrat.lookup_strat_name_tree tree
                      ON tree.strat_name_id = lsn.strat_name_id
                    LEFT JOIN LATERAL unnest(tree.ancestor_concept_ids) AS anc(id)
                      ON true
                    WHERE legend.source_id = :source_id
                    GROUP BY legend.legend_id, legend.strat_name_ids
                ) sub
             )
            UPDATE maps.legend
            SET concept_ids =
            CASE
                WHEN array_length(legend.unit_ids, 1) = 0 OR legend.unit_ids is null
                    THEN COALESCE(more_strat_names.concept_ids, '{{}}')
                ELSE
                    (
                        SELECT array((SELECT DISTINCT unnest(array_cat(COALESCE(more_strat_names.concept_ids, '{{}}'), array_agg(DISTINCT lsn.concept_id)))))
                        FROM macrostrat.unit_strat_names usn
                        JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = usn.strat_name_id
                        WHERE usn.unit_id = ANY(legend.unit_ids)
                    )
                END,
                strat_name_children = COALESCE(more_strat_names.strat_name_children, '{{}}')
            FROM more_strat_names
            WHERE more_strat_names.legend_id = legend.legend_id;
        """,
            {
                "scale_table": Identifier("maps", scale),
                "source_id": source_id,
            },
        )

        print("Ran fifth command")

        # Update best_age_top and best_age_bottom and color
        self.db.run_sql(
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
               WHERE legend.source_id = :source_id
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
            {
                "scale_table": Identifier("maps", scale),
                "source_id": source_id,
            },
        )

        print("Ran sixth command")

        # Nudge same-age units apart. Variants are chosen from each legend's
        # place and size, so two maps of the same ground agree; see
        # utils/legend_color. One read and one write per map -- this used to
        # be an UPDATE per legend row, followed by a name-based homogenization
        # sweep that rewrote every other map at a compatible scale.
        rows = self.db.run_query(
            """
            SELECT
              l.legend_id,
              l.color,
              l.best_age_top,
              l.best_age_bottom,
              ST_X(ST_Centroid(ST_Extent(p.geom))) AS cx,
              ST_Y(ST_Centroid(ST_Extent(p.geom))) AS cy,
              sum(ST_Area(p.geom::geography)) / 1e6 AS area_km
            FROM maps.legend l
            LEFT JOIN maps.map_legend ml ON ml.legend_id = l.legend_id
            LEFT JOIN maps.polygons p
              ON p.map_id = ml.map_id AND p.source_id = l.source_id
            WHERE l.source_id = :source_id
            GROUP BY l.legend_id
            """,
            {"source_id": source_id},
        ).all()

        changes = assign_colors(
            [
                LegendRow(
                    legend_id=r.legend_id,
                    color=r.color,
                    best_age_top=_as_float(r.best_age_top),
                    best_age_bottom=_as_float(r.best_age_bottom),
                    cx=r.cx,
                    cy=r.cy,
                    area_km=_as_float(r.area_km),
                )
                for r in rows
            ]
        )

        if changes:
            self.db.run_sql(
                """
                UPDATE maps.legend l
                SET color = v.color
                FROM unnest(CAST(:legend_ids AS integer[]), CAST(:colors AS text[]))
                  AS v(legend_id, color)
                WHERE l.legend_id = v.legend_id
                """,
                {"legend_ids": list(changes.keys()), "colors": list(changes.values())},
            )

        print(f"Shifted {len(changes)} of {len(rows)} legend colors")
        print("Done")


def _as_float(value):
    if value is None:
        return None
    return float(value)
