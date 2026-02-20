from ..base import Base
from macrostrat.core.database import get_database
from pathlib import Path

here = Path(__file__).parent


def _lookup_unit_intervals():
    db = get_database()
    db.run_sql(here / "sql" / "lookup-unit-intervals.sql")


class LookupUnitIntervals(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        _lookup_unit_intervals()

    def run_old(self):
        second_connection = self.mariadb["raw_connection"]()
        second_cursor = second_connection.cursor()

        db = get_database()

        db.run_sql(here / "sql" / "lookup-unit-intervals.sql")

        # initial query
        units = (
            db.run_query(
                """
            SELECT units.id,
                FO,
                LO,
                f.age_bottom,
                f.interval_name fname,
                f.age_top FATOP,
                l.age_top,
                l.interval_name lname,
                min(u1.t1_age) AS t_age,
                max(u2.t1_age) AS b_age
            FROM units
            JOIN intervals f on FO = f.id
            JOIN intervals l ON LO = l.id
            LEFT JOIN unit_boundaries u1 ON u1.unit_id = units.id
            LEFT JOIN unit_boundaries u2 ON u2.unit_id_2 = units.id
            GROUP BY units.id
            """
            )
            .mappings()
            .fetchall()
        )

        # initialize arrays
        r2 = {}
        r3 = {}
        r4 = {}
        r5 = {}
        r6 = {}
        rLO = {}
        rFO = {}

        row = self.mariadb["cursor"].fetchone()
        for row in units:
            # Use this as the parameters for most of the queries
            params = {"age_bottom": row["age_bottom"], "age_top": row["age_top"]}

            second_cursor.execute(
                """
                SELECT interval_name,intervals.id from intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales on timescale_id = timescales.id
                WHERE timescale = 'international epochs'
                    AND %(age_bottom)s > age_top
                    AND %(age_bottom)s <= age_bottom
                    AND %(age_top)s < age_bottom
                    AND %(age_top)s >= age_top
            """,
                params,
            )
            row2 = second_cursor.fetchone()

            if row2 is None:
                r2["interval_name"] = ""
                r2["id"] = 0
            else:
                r2["interval_name"] = row2["interval_name"]
                r2["id"] = row2["id"]

            second_cursor.execute(
                """
                SELECT interval_name, intervals.id from intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales on timescale_id = timescales.id
                WHERE timescale='international periods'
                    AND %(age_bottom)s > age_top
                    AND %(age_bottom)s <= age_bottom
                    AND %(age_top)s < age_bottom
                    AND %(age_top)s >= age_top
            """,
                params,
            )
            row3 = second_cursor.fetchone()

            if row3 is None:
                r3["interval_name"] = ""
                r3["id"] = 0
            else:
                r3["interval_name"] = row3["interval_name"]
                r3["id"] = row3["id"]

            second_cursor.execute(
                """
                SELECT interval_name FROM intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales on timescale_id = timescales.id
                WHERE timescale = 'international periods'
                    AND age_bottom >= %(age_bottom)s
                    AND age_top < %(age_bottom)s
            """,
                params,
            )
            row_period_FO = second_cursor.fetchone()

            if row_period_FO is None:
                rFO["interval_name"] = ""
                rFO["id"] = 0
            else:
                rFO["interval_name"] = row_period_FO["interval_name"]

            second_cursor.execute(
                """
                SELECT interval_name FROM intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales on timescale_id = timescales.id
                WHERE timescale = 'international periods'
                    AND age_bottom > %(age_top)s
                    AND age_top <= %(age_top)s
            """,
                params,
            )
            row_period_LO = second_cursor.fetchone()

            if row_period_LO is None:
                rLO["interval_name"] = ""
                rLO["id"] = 0
            else:
                rLO["interval_name"] = row_period_LO["interval_name"]

            # International ages
            second_cursor.execute(
                """
                SELECT interval_name, intervals.id from intervals
                JOIN timescales_intervals ON intervals.id = interval_id
                JOIN timescales on timescale_id = timescales.id
                WHERE timescale = 'international ages'
                    AND %(age_bottom)s > age_top
                    AND %(age_bottom)s <= age_bottom
                    AND %(age_top)s < age_bottom
                    AND %(age_top)s >= age_top
            """,
                params,
            )
            row4 = second_cursor.fetchone()

            if row4 is None:
                r4["interval_name"] = ""
                r4["id"] = 0
            else:
                r4["interval_name"] = row4["interval_name"]
                r4["id"] = row4["id"]

            # Any eon, no matter the timescale
            second_cursor.execute(
                """
                SELECT interval_name,intervals.id from intervals
                WHERE interval_type = 'eon'
                    AND %(age_bottom)s > age_top
                    AND %(age_bottom)s <= age_bottom
                    AND %(age_top)s < age_bottom
                    AND %(age_top)s >= age_top
            """,
                params,
            )
            row5 = second_cursor.fetchone()

            if row5 is None:
                r5["interval_name"] = ""
                r5["id"] = 0
            else:
                r5["interval_name"] = row5["interval_name"]
                r5["id"] = row5["id"]

            # Any era, no matter the timescale
            second_cursor.execute(
                """
                SELECT interval_name, intervals.id from intervals
                WHERE interval_type = 'era'
                    AND %(age_bottom)s > age_top
                    AND %(age_bottom)s <= age_bottom
                    AND %(age_top)s < age_bottom
                    AND %(age_top)s >= age_top
            """,
                params,
            )
            row6 = second_cursor.fetchone()

            if row6 is None:
                r6["interval_name"] = ""
                r6["id"] = 0
            else:
                r6["interval_name"] = row6["interval_name"]
                r6["id"] = row6["id"]

            second_cursor.execute(
                """
                INSERT INTO lookup_unit_intervals_new (
                    unit_id,
                    fo_age,
                    b_age,
                    fo_interval,
                    lo_age,
                    t_age,
                    lo_interval,
                    epoch,
                    epoch_id,
                    period,
                    period_id,
                    age,
                    age_id,
                    era,
                    era_id,
                    eon,
                    eon_id,
                    fo_period,
                    lo_period
                )
                VALUES (%(rx_id)s, %(rx_age_bottom)s, %(rx_b_age)s, %(rx_fname)s, %(rx_age_top)s, %(rx_t_age)s, %(rx_lname)s, %(r2_interval_name)s, %(r2_id)s, %(r3_interval_name)s, %(r3_id)s, %(r4_interval_name)s, %(r4_id)s, %(r6_interval_name)s, %(r6_id)s, %(r5_interval_name)s, %(r5_id)s, %(rFO)s, %(rLO)s )
            """,
                {
                    "rx_id": row["id"],
                    "rx_age_bottom": row["age_bottom"],
                    "rx_age_top": row["age_top"],
                    "rx_b_age": row["b_age"],
                    "rx_t_age": row["t_age"],
                    "rx_fname": row["fname"],
                    "rx_lname": row["lname"],
                    "r2_interval_name": r2["interval_name"],
                    "r2_id": r2["id"],
                    "r3_interval_name": r3["interval_name"],
                    "r3_id": r3["id"],
                    "r4_interval_name": r4["interval_name"],
                    "r4_id": r4["id"],
                    "r5_interval_name": r5["interval_name"],
                    "r5_id": r5["id"],
                    "r6_interval_name": r6["interval_name"],
                    "r6_id": r6["id"],
                    "rFO": rFO["interval_name"],
                    "rLO": rLO["interval_name"],
                },
            )

            second_connection.commit()

            row = self.mariadb["cursor"].fetchone()

        # modifiy results for long-ranging units
        self.mariadb["cursor"].execute(
            "UPDATE lookup_unit_intervals_new set period = concat_WS('-',FO_period,LO_period) where period = '' and FO_period not like ''"
        )
        self.mariadb["cursor"].execute(
            "UPDATE lookup_unit_intervals_new set period = eon where period = '' and eon = 'Archean'"
        )
        self.mariadb["cursor"].execute(
            "UPDATE lookup_unit_intervals_new set period = concat_WS('-', FO_interval, LO_period) where FO_interval = 'Archean'"
        )
        self.mariadb["cursor"].execute(
            "UPDATE lookup_unit_intervals_new set period = 'Precambrian' where period = '' and t_age >= 541"
        )

        ## validate results
        self.mariadb["cursor"].execute(
            "SELECT count(*) N, (SELECT count(*) from lookup_unit_intervals_new) nn from units"
        )
        row = self.mariadb["cursor"].fetchone()
        if row["N"] != row["nn"]:
            print("ERROR: inconsistent unit count in lookup_unit_intervals_new table")
