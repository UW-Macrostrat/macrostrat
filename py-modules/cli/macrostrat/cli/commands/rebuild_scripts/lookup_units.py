import sys

from ..base import Base
from ...database import get_db
from pathlib import Path
from os import devnull
from psycopg2.sql import Identifier

here = Path(__file__).parent


class LookupUnits(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        _refresh_lookup_units()


timescale_cache = {}


def _refresh_lookup_units():
    """Bulk refresh method for lookup units table. This is required for the units to show
    up in the API, and is also used to update the lookup table with more detailed time info
    """

    db = get_db()
    db.run_sql(here / "sql" / "lookup-units-01.sql")

    for time_range in ("age", "epoch", "period", "era", "eon"):
        update_timescale(db, time_range)

    # We used to do a loop through all unts here to set age information and update intervals for each unit,
    # but now we are doing it in bulk with the above queries. This presents a quick way to evolve to allow
    # incremental updates on column changes, etc. if we want to do that in the future.

    db.run_sql(here / "sql" / "lookup-units-02.sql")

    # Validate results
    data = db.run_query(
        "SELECT COUNT(*) units_count, (SELECT COUNT(*) FROM lookup_units) lookup_units_count FROM units"
    ).fetchone()
    if data.units_count != data.lookup_units_count:
        print(
            "ERROR: inconsistent unit count in lookup_unit_intervals_new table. ",
            data.lookup_units_count,
            " datas in `lookup_units` and ",
            data.units_count,
            " datas in `units`.",
        )


def update_timescale(db, qtype="age"):
    field_prefix = qtype
    timescale_name = f"international {qtype}s"

    print(f"Updating {qtype}s...")

    age_fields = dict(
        age_field=Identifier(field_prefix),
        age_id_field=Identifier(field_prefix + "_id"),
    )
    db.run_sql(
        """
        WITH ints AS (
           SELECT i.id,
               interval_name,
               age_bottom,
               age_top
           FROM intervals i
           JOIN timescales_intervals ON i.id = interval_id
           JOIN timescales ON timescale_id = timescales.id
           WHERE timescale = :timescale
       )
       UPDATE lookup_units_new SET
           {age_field} = ints.interval_name,
           {age_id_field} = ints.id
       FROM ints
       WHERE b_age > age_top
         AND b_age <= age_bottom
         AND t_age < age_bottom
         AND t_age >= age_top;
       """,
        dict(
            **age_fields,
            timescale=timescale_name,
        ),
    )

    # Coalesce IDs to mimic structure of fields in V1.
    # Not ideal, but works
    db.run_sql(
        """
        UPDATE lookup_units_new SET
            {age_id_field} = 0,
            {age_field} = ''
        WHERE {age_id_field} IS NULL
        """,
        age_fields,
    )
