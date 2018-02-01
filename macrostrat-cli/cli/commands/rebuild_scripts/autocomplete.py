from ..base import Base

class Autocomplete(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        self.mariadb['cursor'].execute("""
            DROP TABLE IF EXISTS autocomplete_new;
        """)
        self.mariadb['connection'].commit()

        # Build the new table
        self.mariadb['cursor'].execute("""
            CREATE TABLE autocomplete_new AS
              SELECT * FROM (
                select id, econ as name, 'econs' as type, 'econ' as category from econs
                union
                select 0 AS id, econ_type AS name, 'econ_types' AS type, 'econ' as category
                FROM econs
                WHERE econ != econ_type
                GROUP BY econ_type
                union
                SELECT 0 AS id, econ_class AS name, 'econ_classes' AS type, 'econ' as category FROM econs GROUP BY econ_class
                union
                select id, environ as name, 'environments' as type, 'environ' as category
                FROM environs
                WHERE environ != environ_class
                union
                select 0 AS id, environ_type AS name, 'environment_types' AS type, 'environ' as category
                FROM environs
                GROUP BY environ_type
                union
                select 0 AS id, environ_class AS name, 'environment_classes' AS type, 'environ' as category
                FROM environs
                GROUP BY environ_class
                union
                select id, concat(lith_att, ' (', att_type, ')') as name, 'lithology_attributes' as type, 'lith_att' as category from lith_atts
                union
                select id, project as name, 'projects' as type, 'project' as category from projects
                union
                SELECT DISTINCT strat_names_meta.concept_id AS id, name, 'strat_name_concepts' AS type, 'strat_name' as category
                FROM strat_names_meta
                JOIN strat_names ON strat_names_meta.concept_id = strat_names.concept_id
                union
                (select id, CONCAT(strat_name, ' ', rank) AS name, 'strat_name_orphans' as type, 'strat_name' as category from strat_names WHERE concept_id = 0)
                union
                select id, col_name as name, 'columns' as type, 'column' as category from cols
                union
                select id, col_group_long as name, 'groups' as type, 'group' as category from col_groups
                union
                SELECT id, lith AS name, 'lithologies' AS type, 'lithology' as category
                FROM liths
                WHERE lith != lith_type AND lith != lith_class
                union
                SELECT 0 AS id, lith_type AS name,  'lithology_types' AS type, 'lithology' AS category
                FROM liths
                WHERE lith_type != lith_class
                GROUP BY lith_type
                union
                SELECT 0 AS id, lith_class AS name, 'lithology_classes' AS type, 'lithology' as category
                FROM liths
                GROUP BY lith_class
                union
                select id, interval_name as name, 'intervals' as type, 'interval' as category from intervals
                union
                SELECT id, mineral AS name, 'minerals' AS type, 'mineral' as category from minerals
                union
                SELECT id, structure as name, 'structures' as type, 'structure' as category from structures
              ) i;
        """)
        self.mariadb['cursor'].close()
        self.mariadb['cursor'] = self.mariadb['connection'].cursor()

        self.mariadb['cursor'].execute("""
          UPDATE autocomplete_new AS a
            INNER JOIN (
              SELECT concept_id, CONCAT(name, COALESCE(CONCAT(' (', interval_name, ')'), '')) AS name
              FROM strat_names_meta
              LEFT JOIN intervals ON intervals.id = strat_names_meta.interval_id
            ) sub ON a.id = sub.concept_id
          SET a.name = sub.name
          WHERE a.id IN (
            SELECT id FROM (
              SELECT id
              FROM autocomplete_new
              WHERE name IN (
                SELECT name
                FROM (
                  SELECT name, type, count(*)
                  FROM autocomplete_new
                  WHERE type = 'strat_name_concepts'
                  GROUP BY name, type
                  HAVING count(*) > 1
                  ORDER BY count(*) desc
                ) a
              )
            ) b
          ) AND type = 'strat_name_concepts';
        """)
        self.mariadb['cursor'].close()
        self.mariadb['cursor'] = self.mariadb['connection'].cursor()

        self.mariadb['cursor'].execute("""
          UPDATE autocomplete_new AS a
            INNER JOIN (
              SELECT DISTINCT strat_names.id, CONCAT(strat_name, ' (', FO_period, ')') AS name
              FROM strat_names
              JOIN unit_strat_names ON strat_names.id = unit_strat_names.strat_name_id
              JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id = unit_strat_names.unit_id
            ) sub ON a.id = sub.id
          SET a.name = sub.name
          WHERE a.id IN (
            SELECT id FROM (
              SELECT id
              FROM autocomplete_new
              WHERE name IN (
                SELECT name
                FROM (
                  SELECT name, type, count(*)
                  FROM autocomplete_new
                  WHERE type = 'strat_name_orphans'
                  GROUP BY name, type
                  HAVING count(*) > 1
                  ORDER BY count(*) desc
                ) a
              )
            ) b
          ) AND type = 'strat_name_orphans';
        """)
        self.mariadb['cursor'].close()
        self.mariadb['cursor'] = self.mariadb['connection'].cursor()

        self.mariadb['cursor'].execute("""
            ALTER TABLE autocomplete rename to autocomplete_old;
            ALTER TABLE autocomplete_new rename to autocomplete;
            DROP TABLE IF EXISTS autocomplete_old;
        """)
        self.mariadb['cursor'].close()
        self.mariadb['connection'].close()
