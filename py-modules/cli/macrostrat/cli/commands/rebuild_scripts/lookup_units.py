from ..base import Base
from ...database import get_db
from pathlib import Path
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
        "SELECT COUNT(*) units_count, (SELECT COUNT(*) FROM lookup_units_new) lookup_units_count FROM units"
    ).fetchone()
    if data.units_count != data.lookup_units_count:
        raise ValueError("Inconsistent units count in lookup_units_new table", data)

    copy_table_into_place(db, "lookup_units")


def copy_table_into_place(
    db, table_name, *, new_table_name=None, old_table_name=None, schema="macrostrat"
):
    if new_table_name is None:
        new_table_name = table_name + "_new"
    if old_table_name is None:
        old_table_name = table_name + "_old"

    db.run_sql(
        """
        TRUNCATE TABLE {table};
        INSERT INTO {table} SELECT * FROM {new_table};
        DROP TABLE IF EXISTS {new_table};
        DROP TABLE IF EXISTS {old_table};
        """,
        dict(
            table=Identifier(schema, table_name),
            new_table=Identifier(schema, new_table_name),
            old_table=Identifier(schema, old_table_name),
        ),
    )


def update_timescale(db, qtype="age"):
    field_prefix = qtype
    timescale_name = f"international {qtype}s"

    print(f"Updating {qtype}s...")

    age_fields = dict(
        interval_name_field=Identifier(field_prefix),
        interval_id_field=Identifier(field_prefix + "_id"),
        table=Identifier("lookup_units_new"),
    )

    update_intervals(db, timescale=timescale_name, **age_fields)

    # Coalesce IDs to mimic structure of fields in V1.
    # Not ideal, but works
    db.run_sql(
        """
        UPDATE {table} SET
            {interval_id_field} = 0,
            {interval_name_field} = ''
        WHERE {interval_id_field} IS NULL
        """,
        age_fields,
    )


def update_intervals(db, *, where_clauses: list[str] = None, **params):
    """Internal version of interval update method which allows more flexible integration
    with different timescales and fields. This is primarily used to allow the lookup_intervals
    update to proceed along similar lines to lookup_units.
    """
    if where_clauses is None:
        where_clauses = [
            "t.b_age > i.age_top",
            "t.b_age <= i.age_bottom",
            "t.t_age < i.age_bottom",
            "t.t_age >= i.age_top",
        ]

    fields = []
    if "interval_name_field" in params:
        fields.append("{interval_name_field} = i.interval_name")
    if "interval_id_field" in params:
        fields.append("{interval_id_field} = i.id")

    sql = """
          WITH ints AS (
              SELECT i.id,
                  interval_name,
                  age_bottom,
                  age_top
              FROM macrostrat.intervals i
              JOIN macrostrat.timescales_intervals ON i.id = interval_id
              JOIN macrostrat.timescales ON timescale_id = macrostrat.timescales.id
              WHERE timescale = :timescale
          )
          UPDATE {table} t SET
              ::fields
          FROM ints i
          """

    sql = sql.replace("::fields", ",\n".join(fields))

    if len(where_clauses) > 0:
        sql += "WHERE " + " AND ".join(where_clauses)

    db.run_sql(sql, params)
