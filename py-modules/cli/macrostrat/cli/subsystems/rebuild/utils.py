from pathlib import Path

from psycopg2.sql import Identifier
from rich.console import Console

here = Path(__file__).parent
console = Console()


def grant_permissions(db):
    """Re-grant read permissions to rockd_reader after any rebuild.

    TODO: this is a bit overbuilt, but it works for now. Ideally we would grant permissions
    on a per-table basis, before we replace the working version, to avoid interruptions.
    """
    db.run_sql(
        """
        GRANT CONNECT ON DATABASE macrostrat TO rockd_reader;
        GRANT USAGE ON SCHEMA macrostrat TO rockd_reader;
        GRANT USAGE ON SCHEMA public TO rockd_reader;
        GRANT USAGE ON SCHEMA topology TO rockd_reader;

        GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO rockd_reader;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO rockd_reader;
        GRANT SELECT ON ALL TABLES IN SCHEMA topology TO rockd_reader;
        """
    )


def validate_counts(db):
    data = db.run_query(
        f"SELECT COUNT(*) units_count, (SELECT COUNT(*) FROM lookup_unit_attrs_api_new) lookup_units_count FROM units"
    ).fetchone()
    if data.units_count != data.lookup_units_count:
        raise ValueError(
            "Inconsistent units count in lookup_unit_attrs_api_new table", data
        )
    else:
        print(
            f"""Validation successful:
units:                 {data.units_count} rows
lookup_unit_attrs_api: {data.lookup_units_count} rows
"""
        )


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


def update_intervals_lookup_units(db, *, where_clauses: list[str] = None, **params):
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


def update_timescale_unit_intervals(db, qtype="age", where_clauses: list[str] = None):
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

    update_intervals_lookup_units(
        db, timescale=timescale_name, where_clauses=where_clauses, **age_fields
    )


def update_timescale_lookup_units(db, qtype="age"):
    field_prefix = qtype
    timescale_name = f"international {qtype}s"

    print(f"Updating {qtype}s...")

    age_fields = dict(
        interval_name_field=Identifier(field_prefix),
        interval_id_field=Identifier(field_prefix + "_id"),
        table=Identifier("lookup_units_new"),
    )

    update_intervals_lookup_units(db, timescale=timescale_name, **age_fields)

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
