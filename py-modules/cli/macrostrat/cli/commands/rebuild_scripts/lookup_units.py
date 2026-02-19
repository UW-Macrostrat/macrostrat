import sys

from ..base import Base
from ...database import get_db
from pathlib import Path

here = Path(__file__).parent


class LookupUnits(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        _refresh_lookup_units()


def _refresh_lookup_units():
    """Bulk refresh method for lookup units table. This is required for the units to show
    up in the API, and is also used to update the lookup table with more detailed time info
    """

    db = get_db()
    db.run_sql(here / "sql" / "lookup-units-01.sql")

    # Gather basic info about all units just inserted so that we can loop through them
    units = db.run_query(
        "SELECT unit_id, t_age, t_int, t_prop, b_age, b_int, b_prop FROM lookup_units_new"
    ).fetchall()

    for idx, unit in enumerate(units):
        # Give some feedback
        sys.stdout.write("%s of %s  \r" % (idx, len(units)))
        sys.stdout.flush()

        # Used to get times
        params = {"t_age": unit["t_age"], "b_age": unit["b_age"]}

        # Get age
        age = get_time(db, "international ages", params)

        # Get epoch
        epoch = get_time(db, "international epochs", params)

        # Get period
        period = get_time(db, "international periods", params)

        # Get era
        era = get_time(db, "international eras", params)

        # Get eon
        eon = get_time(db, "international eons", params)

        # Update the lookup table with detailed time info
        db.run_sql(
            """
            UPDATE lookup_units_new SET
                age = :age,
                age_id = :age_id,
                epoch = :epoch,
                epoch_id = :epoch_id,
                period = :period,
                period_id = :period_id,
                era = :era,
                era_id = :era_id,
                eon = :eon,
                eon_id = :eon_id
            WHERE unit_id = :unit_id
            """,
            {
                "age": age["name"],
                "age_id": age["id"],
                "epoch": epoch["name"],
                "epoch_id": epoch["id"],
                "period": period["name"],
                "period_id": period["id"],
                "era": era["name"],
                "era_id": era["id"],
                "eon": eon["name"],
                "eon_id": eon["id"],
                "unit_id": unit["unit_id"],
            },
        )

        # Check if t_prop == 0, and if so get the next oldest interval of the same scale
        if unit["t_prop"] == 0:
            data = db.run_query(
                """
                SELECT intervals.interval_name, intervals.id, intervals.age_top
                FROM intervals
                JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
                WHERE timescales_intervals.timescale_id IN (
                    SELECT timescale_id FROM timescales_intervals WHERE interval_id = %(int_id)s
                ) AND age_top = (
                    SELECT age_bottom FROM intervals WHERE id = %(int_id)s
                )
                """,
                {"int_id": unit["t_int"]},
            ).fetchone()

            if data is not None:
                # print "Should update top interval ", unit["unit_id"]
                db.run_sql(
                    """
                    UPDATE lookup_units_new SET
                        t_int = %(t_int)s,
                        t_int_name = %(t_int_name)s,
                        t_int_age = %(t_int_age)s,
                        t_prop = 1
                    WHERE unit_id = %(unit_id)s
                    """,
                    {
                        "t_int": data["id"],
                        "t_int_name": data["interval_name"],
                        "t_int_age": data["age_top"],
                        "unit_id": unit["unit_id"],
                    },
                )

        # Check if b_prop == 1, if so get the next younger time interval
        if unit["b_prop"] == 1:
            data = db.run_query(
                """
                SELECT intervals.interval_name, intervals.id, intervals.age_bottom
                FROM intervals
                JOIN timescales_intervals ON intervals.id = timescales_intervals.interval_id
                WHERE timescales_intervals.timescale_id IN (
                    SELECT timescale_id FROM timescales_intervals WHERE interval_id = %(int_id)s
                ) AND age_bottom = (
                    SELECT age_top FROM intervals WHERE id = %(int_id)s
                )
            """,
                {"int_id": unit["b_int"]},
            ).fetchone()

            if data is not None:
                # print "Should update bottom interval ", unit["unit_id"]
                db.run_sql(
                    """
                    UPDATE lookup_units_new SET
                        b_int = %(b_int)s,
                        b_int_name = %(b_int_name)s,
                        b_int_age = %(b_int_age)s,
                        b_prop = 0
                    WHERE unit_id = %(unit_id)s
                    """,
                    {
                        "b_int": data["id"],
                        "b_int_name": data["interval_name"],
                        "b_int_age": data["age_bottom"],
                        "unit_id": unit["unit_id"],
                    },
                )

    db.run_sql(here / "sql" / "lookup-units-02.sql")

    # Validate results
    data = db.run_query(
        """
        SELECT COUNT(*) N, (SELECT COUNT(*) FROM lookup_units) nn FROM units
        """
    ).fetchone()
    if data["N"] != data["nn"]:
        print(
            "ERROR: inconsistent unit count in lookup_unit_intervals_new table. ",
            data["nn"],
            " datas in `lookup_units` and ",
            data["N"],
            " datas in `units`.",
        )


def get_time(db, qtype, params):
    params["type"] = qtype
    data = db.run_query(
        """
        SELECT interval_name, intervals.id FROM intervals
        JOIN timescales_intervals ON intervals.id = interval_id
        JOIN timescales on timescale_id = timescales.id
        WHERE timescale = :type
          AND :b_age > age_top
          AND :b_age <= age_bottom
          AND :t_age < age_bottom
          AND :t_age >= age_top
        """,
        params,
    ).one_or_none()

    if data is not None:
        return {"name": data["interval_name"], "id": data["id"]}
    else:
        return {"name": "", "id": ""}
