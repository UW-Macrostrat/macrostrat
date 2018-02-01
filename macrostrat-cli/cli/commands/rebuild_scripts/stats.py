from ..base import Base

class Stats(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        self.mariadb['cursor'].execute("""
            DROP TABLE IF EXISTS stats_new
        """)
        self.mariadb['cursor'].close()

        self.mariadb['cursor'] = self.mariadb['connection'].cursor()
        self.mariadb['cursor'].execute("""
            CREATE TABLE stats_new AS (
                SELECT
                  projects.id AS project_id,
                  projects.project,
                  unit_counts.columns,
                  unit_counts.packages,
                  unit_counts.units,
                  collection_counts.pbdb_collections,
                  measure_counts.measurements
                FROM projects
                JOIN (
                  SELECT project_id, count(distinct col_id) AS columns, count(distinct section_id) AS packages, count(distinct unit_id) AS units
                  FROM (
                    SELECT DISTINCT project_id, units_sections.section_id, units_sections.col_id, units_sections.unit_id
                    FROM units_sections
                    JOIN cols ON cols.id = units_sections.col_id
                    WHERE cols.status_code = 'active'
                  ) distinct_units
                  GROUP BY distinct_units.project_id
                ) AS unit_counts ON unit_counts.project_id = projects.id
                JOIN (
                  SELECT project_id, count(distinct id) AS measurements
                  FROM (
                    SELECT DISTINCT project_id, measures.id
                    FROM cols
                    JOIN units_sections ON cols.id = units_sections.col_id
                    LEFT JOIN unit_measures ON unit_measures.unit_id = units_sections.unit_id
                    LEFT JOIN measures ON unit_measures.measuremeta_id = measures.measuremeta_id
                    WHERE cols.status_code = 'active'
                  ) AS distinct_measures
                  GROUP BY distinct_measures.project_id
                ) AS measure_counts ON measure_counts.project_id = projects.id
                JOIN (
                  SELECT project_id, count(distinct collection_no) AS pbdb_collections
                  FROM (
                    SELECT DISTINCT project_id, collection_no
                    FROM cols
                    JOIN units_sections ON units_sections.col_id = cols.id
                    LEFT JOIN pbdb_matches ON pbdb_matches.unit_id = units_sections.unit_id
                    WHERE cols.status_code = 'active'
                  ) AS distinct_collections
                  GROUP BY distinct_collections.project_id
                ) AS collection_counts ON collection_counts.project_id = projects.id
                WHERE project IN ('North America','New Zealand','Caribbean','Deep Sea')
            )
        """)

        self.mariadb['cursor'].execute("""
            ALTER TABLE stats_new ADD COLUMN burwell_polygons integer default 0;
        """)

        self.mariadb['cursor'].close()
        self.mariadb['cursor'] = self.mariadb['connection'].cursor()

        self.pg['cursor'].execute("""
            select count(*)
            FROM (SELECT map_id FROM maps.tiny
            UNION SELECT map_id FROM maps.small
            UNION SELECT map_id FROM maps.medium
            UNION SELECT map_id FROM maps.large) foo
        """)
        count = self.pg['cursor'].fetchone()[0]

        self.mariadb['cursor'].execute("UPDATE stats_new SET burwell_polygons = %d" % count)
        self.mariadb['connection'].commit()

        self.mariadb['cursor'].execute("""
            ALTER TABLE stats rename to stats_old;
            ALTER TABLE stats_new rename to stats;
            DROP TABLE IF EXISTS stats;
        """)

        self.mariadb['cursor'].close()
        self.mariadb['connection'].close()

        self.pg['connection'].close()
