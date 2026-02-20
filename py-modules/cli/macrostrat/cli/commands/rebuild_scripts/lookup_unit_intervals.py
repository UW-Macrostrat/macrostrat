from ..base import Base
from macrostrat.core.database import get_database
from pathlib import Path
from .lookup_units import update_intervals, copy_table_into_place
from psycopg2.sql import Identifier

here = Path(__file__).parent


def _lookup_unit_intervals():
    db = get_database()
    db.run_sql(here / "sql" / "lookup-unit-intervals-01.sql")

    for time_range in ("age", "epoch", "period", "era", "eon"):
        update_timescale(db, time_range)

    shared = dict(
        timescale="international ages",
        table=Identifier("lookup_unit_intervals_new"),
    )

    # Uses fo_age and lo_age instead of t_age and b_age, to work at the interval level
    # first overlap period (name only)
    update_intervals(
        db,
        interval_name_field=Identifier("fo_period"),
        where_clauses=["i.age_bottom >= t.fo_age", "i.age_top < t.fo_age"],
        **shared,
    )

    # last overlap period (name only)
    update_intervals(
        db,
        interval_name_field=Identifier("lo_period"),
        where_clauses=["i.age_bottom > t.lo_age", "i.age_top <= t.lo_age"],
        **shared,
    )

    db.run_sql(here / "sql" / "lookup-unit-intervals-02.sql")

    ## validate results
    res = db.run_query(
        "SELECT count(*) units_count, (SELECT count(*) from lookup_unit_intervals_new) units_intervals_count from units"
    ).one()

    if res.units_count != res.units_intervals_count:
        raise ValueError(
            "Inconsistent unit count in lookup_unit_intervals_new table", res
        )

    copy_table_into_place(db, "lookup_unit_intervals", schema="macrostrat")


class LookupUnitIntervals(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        _lookup_unit_intervals()


def update_timescale(db, qtype="age", where_clauses: list[str] = None):
    field_prefix = qtype
    timescale_name = f"international {qtype}s"

    print(f"Updating {qtype}s...")

    where_clauses = [
        # t = unit, i = matched interval
        "t.fo_age > i.age_top",
        "t.fo_age <= i.age_bottom",
        "t.lo_age < i.age_bottom",
        "t.lo_age >= i.age_top",
    ]

    age_fields = dict(
        interval_name_field=Identifier(field_prefix),
        interval_id_field=Identifier(field_prefix + "_id"),
        table=Identifier("lookup_unit_intervals_new"),
    )

    update_intervals(
        db, timescale=timescale_name, where_clauses=where_clauses, **age_fields
    )
