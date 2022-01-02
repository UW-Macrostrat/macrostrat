from ..base import Base


class LookupStratNames(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        lookup_rank_children = {
            "sgp": ["SGp", "Gp", "SubGp", "Fm", "Mbr", "Bed"],
            "gp": ["Gp", "SubGp", "Fm", "Mbr", "Bed"],
            "subgp": ["SubGp", "Fm", "Mbr", "Bed"],
            "fm": ["Fm", "Mbr", "Bed"],
            "mbr": ["Mbr", "Bed"],
            "bed": ["Bed"],
        }

        # Copy structure to new table
        self.mariadb["cursor"].execute(
            """
            DROP TABLE IF EXISTS lookup_strat_names_new;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            DROP TABLE IF EXISTS lookup_strat_names_old;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            CREATE TABLE lookup_strat_names_new LIKE lookup_strat_names;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        # Get all the strat names
        self.mariadb["cursor"].execute(
            """
            SELECT *
            FROM strat_names
            WHERE rank != ''
            ORDER BY strat_name ASC
        """
        )

        update_connection = self.mariadb["raw_connection"]()
        update_cursor = update_connection.cursor()

        for strat_name in self.mariadb["cursor"]:
            rank_id = strat_name["rank"] + "_id"
            rank_name = strat_name["rank"] + "_name"

            update_cursor.execute(
                """
              INSERT INTO lookup_strat_names_new (ref_id, concept_id, strat_name_id, strat_name, rank, """
                + rank_id
                + """, """
                + rank_name
                + """)
              VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                [
                    strat_name["ref_id"],
                    strat_name["concept_id"],
                    strat_name["id"],
                    strat_name["strat_name"],
                    strat_name["rank"],
                    strat_name["id"],
                    strat_name["strat_name"],
                ],
            )
            update_connection.commit()

            has_parent = True
            name_id = strat_name["id"]

            while has_parent:
                # Get the parent of this unit
                update_cursor.execute(
                    """
                    SELECT this_name, strat_name, strat_names.id id, rank
                    FROM strat_tree
                    JOIN strat_names ON this_name = strat_names.id
                    WHERE that_name = %s and rel = 'parent' and rank != ''
                """,
                    [name_id],
                )
                parent = update_cursor.fetchone()

                update_cursor.close()
                update_cursor = update_connection.cursor()

                if parent is None:
                    name_id = 0
                else:
                    name_id = parent["id"]
                    parent_rank_id = parent["rank"] + "_id"
                    parent_rank_name = parent["rank"] + "_name"

                if name_id > 0:
                    update_cursor.execute(
                        """
                      UPDATE lookup_strat_names_new
                      SET """
                        + parent_rank_id
                        + """ = %s, """
                        + parent_rank_name
                        + """ = %s
                      WHERE strat_name_id = %s
                    """,
                        [parent["id"], parent["strat_name"], strat_name["id"]],
                    )
                    update_connection.commit()
                else:
                    has_parent = False

                sql = """
                UPDATE lookup_strat_names_new SET t_units = (
                  SELECT COUNT(*)
                  FROM unit_strat_names
                  LEFT JOIN units_sections ON unit_strat_names.unit_id = units_sections.unit_id
                  LEFT JOIN cols ON units_sections.col_id = cols.id
                  WHERE unit_strat_names.strat_name_id IN (
                    SELECT strat_name_id
                    FROM lookup_strat_names
                    WHERE %s_id = %s AND rank IN """ % (
                    strat_name["rank"].lower(),
                    strat_name["id"],
                )

                placeholders = ["%s"] * len(
                    lookup_rank_children[strat_name["rank"].lower()]
                )
                sql += (
                    " ("
                    + ",".join(placeholders)
                    + ")) AND cols.status_code = 'active') WHERE strat_name_id = %s"
                )
                params = [x for x in lookup_rank_children[strat_name["rank"].lower()]]
                params.append(strat_name["id"])
                update_cursor.execute(sql, params)
                update_connection.commit()

        update_cursor.close()
        update_connection.close()

        # Populate `early_age` and `late_age`
        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_strat_names_new lsn
          LEFT JOIN (
            SELECT strat_name_id, max(b_age) AS early_age, min(t_age) AS late_age
            FROM lookup_strat_names_new
            LEFT JOIN unit_strat_names USING (strat_name_id)
            LEFT JOIN lookup_unit_intervals USING (unit_id)
            GROUP BY strat_name_id
          ) AS sub USING (strat_name_id)
          SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
        """
        )
        self.mariadb["connection"].commit()

        # Populate rank_name
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new SET rank_name =
            CASE
            	WHEN SUBSTRING_INDEX(strat_name, ' ', -1) IN ('Suite', 'Volcanics', 'Complex', 'Melange', 'Series', 'Supersuite', 'Tongue', 'Lens', 'Lentil', 'Drift', 'Metamorphics', 'Sequence', 'Supersequence', 'Intrusives', 'Measures', 'Division', 'Subsuite')
                	THEN strat_name
                WHEN LOWER(SUBSTRING_INDEX(strat_name, ' ', -1)) IN (SELECT lith FROM liths) AND rank = 'fm'
                	THEN strat_name
                 WHEN SUBSTRING_INDEX(strat_name, ' ', -1) = 'Beds' AND rank = 'Bed'
                    THEN strat_name
            	WHEN rank = 'SGp' THEN
                	CONCAT(strat_name, ' Supergroup')
            	WHEN rank = 'Gp' THEN
                	CONCAT(strat_name, ' Group')
              WHEN rank = 'SubGp' THEN
                  CONCAT(strat_name, ' Subgroup')
                WHEN rank = 'Fm' THEN
                	CONCAT(strat_name, ' Formation')
                WHEN rank = 'Mbr' THEN
                	CONCAT(strat_name, ' Member')
                WHEN rank = 'Bed' THEN
                	CONCAT(strat_name, ' Bed')
            END
        """
        )
        self.mariadb["connection"].commit()

        # Validate results
        self.mariadb["cursor"].execute(
            """
            SELECT count(*) sn, (SELECT count(*) from lookup_strat_names_new) lsn
            FROM strat_names
            WHERE rank != ''
        """
        )
        row = self.mariadb["cursor"].fetchone()
        if row["sn"] != row["lsn"]:
            print(
                "   ERROR: inconsistent strat_name count in lookup table. Found %s rows in lookup_strat_names_new"
                % (row["lsn"],)
            )
            sys.exit(1)

        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        # Populate the fields `parent` and `tree`
        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_strat_names_new
          SET parent = CASE
            WHEN bed_id > 0 AND strat_name_id != bed_id THEN bed_id
            WHEN mbr_id > 0 AND strat_name_id != mbr_id THEN mbr_id
            WHEN fm_id > 0 AND strat_name_id != fm_id THEN fm_id
            WHEN subgp_id > 0 AND strat_name_id != subgp_id THEN subgp_id
            WHEN gp_id > 0 AND strat_name_id != gp_id THEN gp_id
            WHEN sgp_id > 0 AND strat_name_id != sgp_id THEN sgp_id
            ELSE strat_name_id
          END,
            tree = CASE
            WHEN sgp_id > 0 THEN sgp_id
            WHEN gp_id > 0 THEN gp_id
            WHEN subgp_id > 0 THEN subgp_id
            WHEN fm_id > 0 THEN fm_id
            WHEN mbr_id > 0 THEN mbr_id
            WHEN bed_id > 0 THEN bed_id
            ELSE tree = 0
          END
        """
        )
        self.mariadb["connection"].commit()

        # Group by concept_id and fill in NULL ages
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new lsn
             LEFT JOIN (
               SELECT concept_id, max(b_age) AS early_age, min(t_age) AS late_age
               FROM lookup_strat_names_new
               LEFT JOIN unit_strat_names USING (strat_name_id)
               LEFT JOIN lookup_unit_intervals USING (unit_id)
               WHERE concept_id != 0
               GROUP BY strat_name_id
             ) AS sub USING (concept_id)
             SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
             WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL
        """
        )
        self.mariadb["connection"].commit()

        # Group by concept_id, but using strat names meta
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new lsn
            LEFT JOIN (
                SELECT concept_id, b.age_bottom, t.age_top
                FROM strat_names_meta
                JOIN intervals b on b.id = b_int
                JOIN intervals t ON t.id = t_int
            ) AS sub USING (concept_id)
            SET lsn.early_age = sub.age_bottom, lsn.late_age = sub.age_top
            WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL
        """
        )
        self.mariadb["connection"].commit()

        # Group by parent and fill in NULL ages
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new lsn
             LEFT JOIN (
               SELECT parent, max(b_age) AS early_age, min(t_age) AS late_age
               FROM lookup_strat_names_new
               LEFT JOIN unit_strat_names USING (strat_name_id)
               LEFT JOIN lookup_unit_intervals USING (unit_id)
               GROUP BY parent
             ) AS sub USING (parent)
             SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
             WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL
        """
        )
        self.mariadb["connection"].commit()

        # Group by tree and fill in NULL ages
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new lsn
             LEFT JOIN (
               SELECT tree, max(b_age) AS early_age, min(t_age) AS late_age
               FROM lookup_strat_names
               LEFT JOIN unit_strat_names USING (strat_name_id)
               LEFT JOIN lookup_unit_intervals USING (unit_id)
               GROUP BY tree
             ) AS sub USING (tree)
             SET lsn.early_age = sub.early_age, lsn.late_age = sub.late_age
             WHERE lsn.early_age IS NULL AND lsn.late_age IS NULL
        """
        )
        self.mariadb["connection"].commit()

        # Populate the fields `b_period` and `t_period`
        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_strat_names_new
          SET b_period = (
            SELECT interval_name
            FROM macrostrat.intervals
            JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
            JOIN timescales ON timescales.id = timescales_intervals.timescale_id
            WHERE age_bottom >= early_age AND age_top <= early_age
            AND timescales.id = 20
            LIMIT 1
          );
        """
        )
        self.mariadb["connection"].commit()

        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_strat_names_new
          SET t_period = (
            SELECT interval_name
            FROM intervals
            JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
            JOIN timescales ON timescales.id = timescales_intervals.timescale_id
            WHERE age_bottom >= late_age AND age_top <= late_age
            AND timescales.id = 20
            LIMIT 1
          );
        """
        )
        self.mariadb["connection"].commit()

        # Update containing interval for names not explicitly matched to units but have a concept_id
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new
            JOIN strat_names_meta USING (concept_id)
            JOIN intervals t on t.id = t_int
            JOIN intervals b on b.id = b_int
            SET c_interval = (
                SELECT interval_name
                FROM intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales ON timescale_id = timescales.id
                WHERE timescale = 'international'
                    AND b.age_bottom > age_top
                    AND b.age_bottom <= age_bottom
                    AND t.age_top < age_bottom
                    AND t.age_top >= age_top
                ORDER BY age_bottom - age_top
                LIMIT 1
            ),
            b_period = (
                SELECT interval_name
                FROM intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales ON timescale_id = timescales.id
                WHERE timescale = 'international periods'
                    AND b.age_bottom > age_top
                    AND b.age_bottom <= age_bottom
                    AND b.age_top < age_bottom
                    AND b.age_top >= age_top
                ORDER BY age_bottom - age_top
                LIMIT 1
            ),
            t_period = (
                SELECT interval_name
                FROM intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales ON timescale_id = timescales.id
                WHERE timescale = 'international periods'
                    AND t.age_bottom > age_top
                    AND t.age_bottom <= age_bottom
                    AND t.age_top < age_bottom
                    AND t.age_top >= age_top
                ORDER BY age_bottom - age_top
                LIMIT 1
            )
            WHERE c_interval IS NULL and t_int > 0 and b_int > 0;
        """
        )
        self.mariadb["connection"].commit()

        # alter table lookup_strat_names add column name_no_lith varchar(100);
        ### Remove lithological terms from strat names ###

        # Get a list of lithologies
        self.mariadb["cursor"].execute(
            """
            SELECT lith FROM liths
        """
        )
        lith_results = self.mariadb["cursor"].fetchall()
        lithologies = [lith["lith"] for lith in lith_results]
        plural_lithologies = [lith["lith"] + "s" for lith in lith_results]
        other_terms = [
            "beds",
            "volcanics",
            "and",
            "complex",
            "member",
            "formation",
            "lower",
            "upper",
        ]

        lithologies = lithologies + plural_lithologies + other_terms

        update_connection = self.mariadb["raw_connection"]()
        update_cursor = update_connection.cursor()
        # Fetch all strat names
        self.mariadb["cursor"].execute(
            """
            SELECT strat_name_id, strat_name FROM lookup_strat_names_new
        """
        )
        for strat_name in self.mariadb["cursor"].fetchall():
            split_name = strat_name["strat_name"].split(" ")

            name_no_lith = " ".join(
                [name for name in split_name if name.lower() not in lithologies]
            )
            print(strat_name["strat_name_id"], name_no_lith)
            update_cursor.execute(
                """
              UPDATE lookup_strat_names_new SET name_no_lith = %(name_no_lith)s WHERE strat_name_id = %(strat_name_id)s
            """,
                {
                    "name_no_lith": name_no_lith,
                    "strat_name_id": strat_name["strat_name_id"],
                },
            )
            update_connection.commit()

        update_connection.commit()
        update_connection.close()
        # self.mariadb['connection'].commit()

        # Make sure all names have an early and late_age
        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_strat_names_new
          SET early_age = (
            SELECT age_bottom
            FROM macrostrat.intervals
            WHERE interval_name = b_period
            LIMIT 1
          ), late_age = (
            SELECT age_top
            FROM macrostrat.intervals
            WHERE interval_name = t_period
            LIMIT 1
          ) WHERE early_age IS NULL AND late_age IS NULL;
        """
        )
        self.mariadb["connection"].commit()

        # Populate containing interval
        self.mariadb["cursor"].execute(
            """
            UPDATE lookup_strat_names_new
            SET c_interval = (
                SELECT interval_name from intervals
            	JOIN timescales_intervals ON intervals.id = interval_id
            	JOIN timescales on timescale_id = timescales.id
            	WHERE timescale = 'international'
            		AND early_age > age_top
            		AND early_age <= age_bottom
            		AND late_age < age_bottom
            		AND late_age >= age_top
            		ORDER BY age_bottom - age_top
                    LIMIT 1
            )
        """
        )
        self.mariadb["connection"].commit()

        # Out with the old, in with the new
        self.mariadb["cursor"].execute("TRUNCATE lookup_strat_names")
        self.mariadb["cursor"].execute(
            "INSERT INTO lookup_strat_names SELECT * FROM lookup_strat_names_new"
        )
        self.mariadb["cursor"].close()

        self.mariadb["cursor"] = self.mariadb["connection"].cursor()
        self.mariadb["cursor"].execute("DROP TABLE lookup_strat_names_new")
        self.mariadb["cursor"].close()
