import decimal
import json
from collections import defaultdict

from ..base import Base


class LookupUnitsAttrsAPI(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        def check_for_decimals(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            raise TypeError

        update_conn = self.mariadb["raw_connection"]()
        update_cur = update_conn.cursor()

        # Create room for the new data
        self.mariadb["cursor"].execute(
            """
            DROP TABLE IF EXISTS lookup_unit_attrs_api_new;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            DROP TABLE IF EXISTS lookup_unit_attrs_api_old;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            CREATE TABLE lookup_unit_attrs_api_new LIKE lookup_unit_attrs_api;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        # First recompute and populate comp_prop
        self.mariadb["cursor"].execute(
            """
            UPDATE unit_liths
            JOIN (
                SELECT
                  a.unit_id,
                  (5 / (COALESCE(bdom, 0) + (adom * 5))) AS dom_p
                  FROM (
                      SELECT
                          unit_id,
                          count(id) adom,
                          'dom' AS dom
                      FROM unit_liths
                      WHERE dom = 'dom'
                      GROUP BY unit_id
                  ) a
                  LEFT JOIN (
                      SELECT
                          unit_id,
                          count(id) bdom,
                          'sub' AS dom
                      FROM unit_liths
                      WHERE dom = 'sub'
                      GROUP BY unit_id
                  ) b ON b.unit_id = a.unit_id
            ) d ON d.unit_id = unit_liths.unit_id AND 'dom' = unit_liths.dom
            SET unit_liths.comp_prop = d.dom_p;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            UPDATE unit_liths
            JOIN (
                SELECT
                  a.unit_id,
                  (1 / (COALESCE(bdom, 0) + (adom * 5))) AS sub_p
                  FROM (
                      SELECT
                          unit_id,
                          count(id) adom,
                          'dom' AS dom
                      FROM unit_liths
                      WHERE dom = 'dom'
                      GROUP BY unit_id
                  ) a
                  LEFT JOIN (
                      SELECT
                          unit_id,
                          count(id) bdom,
                          'sub' AS dom
                      FROM unit_liths
                      WHERE dom = 'sub'
                      GROUP BY unit_id
                  ) b ON b.unit_id = a.unit_id
            ) s ON s.unit_id = unit_liths.unit_id AND 'sub' = unit_liths.dom
            SET unit_liths.comp_prop = s.sub_p;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        ### Next handle lithologies ###
        self.mariadb["cursor"].execute(
            """
          SELECT unit_id, lith_id, lith, lith_type, lith_class, comp_prop, GROUP_CONCAT(lith_atts.lith_att SEPARATOR '|') AS lith_atts
          FROM unit_liths
          LEFT JOIN liths ON lith_id = liths.id
          LEFT JOIN unit_liths_atts ON unit_liths.id = unit_liths_atts.unit_lith_id
          LEFT JOIN lith_atts ON unit_liths_atts.lith_att_id = lith_atts.id
          GROUP BY unit_liths.id
          ORDER BY unit_id ASC
        """
        )

        # Iterate on each row and insert
        unit = self.mariadb["cursor"].fetchone()
        unit_attrs = []
        current_unit_id = None
        while unit is not None:
            if unit["unit_id"] != current_unit_id:
                update_cur.execute(
                    """
                  INSERT INTO lookup_unit_attrs_api_new (unit_id, lith) VALUES (%s, %s)
                """,
                    [
                        current_unit_id,
                        json.dumps(unit_attrs, default=check_for_decimals),
                    ],
                )
                unit_attrs = []
                current_unit_id = unit["unit_id"]

            atts = []
            if unit["lith_atts"] is not None:
                atts = unit["lith_atts"].split("|")
            entry = {
                "lith_id": unit["lith_id"],
                "atts": atts,
                "name": unit["lith"],
                "type": unit["lith_type"],
                "class": unit["lith_class"],
                "prop": unit["comp_prop"],
            }
            unit_attrs.append(entry)
            unit = self.mariadb["cursor"].fetchone()

        update_cur.close()
        update_cur = update_conn.cursor()
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        ### Next handle environments ###
        self.mariadb["cursor"].execute(
            """
          SELECT unit_id, environ_id, environ, environ_type, environ_class
          FROM unit_environs
          LEFT JOIN environs ON environ_id = environs.id
          ORDER BY unit_id ASC
        """
        )

        unit_a = self.mariadb["cursor"].fetchone()
        unit_a_attrs = []
        current_unit_a_id = None
        while unit_a is not None:
            if unit_a["unit_id"] != current_unit_a_id:
                update_cur.execute(
                    """
                  UPDATE lookup_unit_attrs_api_new SET environ = %s WHERE unit_id = %s
                """,
                    [
                        json.dumps(unit_a_attrs, default=check_for_decimals),
                        current_unit_a_id,
                    ],
                )
                unit_a_attrs = []
                current_unit_a_id = unit_a["unit_id"]

            entry = {
                "environ_id": unit_a["environ_id"],
                "name": unit_a["environ"],
                "type": unit_a["environ_type"],
                "class": unit_a["environ_class"],
            }
            unit_a_attrs.append(entry)
            unit_a = self.mariadb["cursor"].fetchone()

        update_cur.close()
        update_cur = update_conn.cursor()
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        ### Next handle econs ###
        self.mariadb["cursor"].execute(
            """
          SELECT unit_id, econ_id, econ, econ_type, econ_class
          FROM unit_econs
          LEFT JOIN econs ON econ_id = econs.id
          ORDER BY unit_id ASC
        """
        )

        unit_b = self.mariadb["cursor"].fetchone()
        unit_b_attrs = []
        current_unit_b_id = None
        while unit_b is not None:
            if unit_b["unit_id"] != current_unit_b_id:
                update_cur.execute(
                    """
                  UPDATE lookup_unit_attrs_api_new SET econ = %s WHERE unit_id = %s
                """,
                    [
                        json.dumps(unit_b_attrs, default=check_for_decimals),
                        current_unit_b_id,
                    ],
                )
                unit_b_attrs = []
                current_unit_b_id = unit_b["unit_id"]

            entry = {
                "econ_id": unit_b["econ_id"],
                "name": unit_b["econ"],
                "type": unit_b["econ_type"],
                "class": unit_b["econ_class"],
            }
            unit_b_attrs.append(entry)
            unit_b = self.mariadb["cursor"].fetchone()

        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_unit_attrs_api_new SET econ = '[]' WHERE econ IS NULL
        """
        )
        update_cur.close()
        update_cur = update_conn.cursor()
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        ### Next handle measurements short ###
        self.mariadb["cursor"].execute(
            """
          SELECT DISTINCT
          measurement_class,
          measurement_type,
          unit_id
          FROM measurements JOIN measures ON measures.measurement_id = measurements.id
          JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
          JOIN unit_measures ON measuremeta.id = unit_measures.measuremeta_id
        """
        )

        measurement = self.mariadb["cursor"].fetchone()
        measurement_attrs = []
        current_measurement_id = None
        while measurement is not None:
            if measurement["unit_id"] != current_measurement_id:
                update_cur.execute(
                    """
                  UPDATE lookup_unit_attrs_api_new SET measure_short = %s WHERE unit_id = %s
                """,
                    [
                        json.dumps(measurement_attrs, default=check_for_decimals),
                        current_measurement_id,
                    ],
                )
                measurement_attrs = []
                current_measurement_id = measurement["unit_id"]

            entry = {
                "measure_class": measurement["measurement_class"],
                "measure_type": measurement["measurement_type"],
            }
            measurement_attrs.append(entry)
            measurement = self.mariadb["cursor"].fetchone()

        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_unit_attrs_api_new SET measure_short = '[]' WHERE measure_short IS NULL
        """
        )

        update_cur.close()
        update_cur = update_conn.cursor()
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        ### Next handle measurements_long ####
        self.mariadb["cursor"].execute(
            """
          SELECT measurements.id AS measure_id,
          measurement_class AS measure_class,
          measurement_type AS measure_type,
          measurement AS measure,
          round(avg(measure_value),5) AS mean,
          round(stddev(measure_value),5) AS stddev,
          count(unit_measures.id) AS n,
          units,
          unit_id
          FROM measures JOIN measurements ON measures.measurement_id = measurements.id
          JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
          JOIN unit_measures ON measuremeta.id = unit_measures.measuremeta_id
          GROUP BY unit_id, measurements.id
        """
        )

        measurement_b = self.mariadb["cursor"].fetchone()
        measurement_b_attrs = []
        current_measurement_b_id = None
        while measurement_b is not None:
            if measurement_b["unit_id"] != current_measurement_b_id:
                update_cur.execute(
                    """
                  UPDATE lookup_unit_attrs_api_new SET measure_long = %s WHERE unit_id = %s
                """,
                    [
                        json.dumps(measurement_b_attrs, default=check_for_decimals),
                        current_measurement_b_id,
                    ],
                )
                measurement_b_attrs = []
                current_measurement_b_id = measurement_b["unit_id"]

            entry = {
                "measure_id": measurement_b["measure_id"],
                "measure": measurement_b["measure"],
                "mean": measurement_b["mean"],
                "stddev": measurement_b["stddev"],
                "n": measurement_b["n"],
                "unit": measurement_b["units"],
            }
            measurement_b_attrs.append(entry)
            measurement_b = self.mariadb["cursor"].fetchone()

        update_cur.close()
        update_conn.close()

        self.mariadb["cursor"].execute(
            """
          UPDATE lookup_unit_attrs_api_new SET measure_long = '[]' WHERE measure_long IS NULL
        """
        )
        self.mariadb["connection"].commit()

        self.mariadb["cursor"].execute(
            """
            TRUNCATE TABLE lookup_unit_attrs_api;
        """
        )
        self.mariadb["cursor"].close()
        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            INSERT INTO lookup_unit_attrs_api SELECT * FROM lookup_unit_attrs_api_new;
        """
        )
        self.mariadb["cursor"].close()

        self.mariadb["cursor"] = self.mariadb["connection"].cursor()

        self.mariadb["cursor"].execute(
            """
            DROP TABLE IF EXISTS lookup_unit_attrs_api_new;
        """
        )

        self.mariadb["cursor"].close()
        self.mariadb["connection"].close()
