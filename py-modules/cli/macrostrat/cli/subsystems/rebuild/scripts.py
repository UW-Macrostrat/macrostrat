from pathlib import Path

from psycopg2.sql import Identifier
from rich.console import Console
from rich.progress import Progress, track

from macrostrat.core.database import get_database
from macrostrat.core.exc import MacrostratError

here = Path(__file__).parent
console = Console()


# ---------------------------------------------------------------------------
# Shared helpers (from lookup_units.py)
# ---------------------------------------------------------------------------


def validate_counts(db):
    data = db.run_query(
        "SELECT COUNT(*) units_count, (SELECT COUNT(*) FROM lookup_unit_attrs_api_new) lookup_units_count FROM units"
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


# from lookup_unit_intervals
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


# ---------------------------------------------------------------------------
# Scripts (unchanged logic, just consolidated)
# ---------------------------------------------------------------------------


class Autocomplete:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "autocomplete.sql")


class UnitBoundaries:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "unit-boundaries.sql")


class Stats:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "stats.sql")


class StratNameFootprints:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "strat-name-footprints.sql")


class LookupUnits:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "lookup-units-01.sql")

        for time_range in ("age", "epoch", "period", "era", "eon"):
            update_timescale_lookup_units(db, time_range)
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


class LookupUnitIntervals:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "lookup-unit-intervals-01.sql")

        for time_range in ("age", "epoch", "period", "era", "eon"):
            update_timescale_unit_intervals(db, time_range)

        shared = dict(
            timescale="international ages",
            table=Identifier("lookup_unit_intervals_new"),
        )

        # Uses fo_age and lo_age instead of t_age and b_age, to work at the interval level
        # first overlap period (name only)
        update_intervals_lookup_units(
            db,
            interval_name_field=Identifier("fo_period"),
            where_clauses=["i.age_bottom >= t.fo_age", "i.age_top < t.fo_age"],
            **shared,
        )

        # last overlap period (name only)
        update_intervals_lookup_units(
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


class LookupUnitAttrsApi:
    def run(self):
        db = get_database()
        db.run_sql(here / "sql" / "lookup-unit-attrs-api-01.sql")
        validate_counts(db)
        copy_table_into_place(db, "lookup_unit_attrs_api")


class LookupStratNames:
    def run(self):
        db = get_database()
        db.run_sql("SET SEARCH_PATH TO macrostrat, public;")

        self.part_1()
        self.part_2()

    def part_1(self):
        db = get_database()

        lookup_rank_children = {
            "sgp": ["SGp", "Gp", "SubGp", "Fm", "Mbr", "Bed"],
            "gp": ["Gp", "SubGp", "Fm", "Mbr", "Bed"],
            "subgp": ["SubGp", "Fm", "Mbr", "Bed"],
            "fm": ["Fm", "Mbr", "Bed"],
            "mbr": ["Mbr", "Bed"],
            "bed": ["Bed"],
        }

        db.run_sql("SET SEARCH_PATH TO macrostrat, public;")

        db.run_sql(here / "sql" / "lookup-strat-names-01.sql")

        # Get all the strat names
        res = db.run_query(
            """
            SELECT *
            FROM macrostrat.strat_names
            WHERE rank != ''
            ORDER BY strat_name
            """
        )

        strat_names = res.all()
        n_strat_names = len(strat_names)

        ranks = set([strat_name.rank for strat_name in strat_names])

        with Progress() as progress:
            task = progress.add_task("Inserting strat names...", total=n_strat_names)
            progress.update(task, total=n_strat_names)
            for rank in ranks:
                _rank = str(rank).lower()
                rank_id = _rank + "_id"
                rank_name = _rank + "_name"

                params = dict(
                    rank=rank,
                    rank_id_col=Identifier(rank_id),
                    rank_name_col=Identifier(rank_name),
                )

                res = db.run_query(
                    """
                    INSERT INTO macrostrat.lookup_strat_names_new (
                        ref_id,
                        concept_id,
                        strat_name_id,
                        strat_name,
                        rank,
                        {rank_id_col},
                        {rank_name_col}
                    )
                    SELECT
                        ref_id,
                        concept_id,
                        id,
                        strat_name,
                        (rank::text)::macrostrat.lookup_strat_names_rank,
                        id,
                        strat_name
                    FROM macrostrat.strat_names
                    WHERE rank = :rank
                    """,
                    params,
                )
                n_inserted = res.rowcount
                db.session.commit()
                progress.update(task, advance=n_inserted)

            db.session.commit()

            for i, strat_name in enumerate(
                progress.track(
                    strat_names,
                    description="Linking parent strat names...",
                    total=n_strat_names,
                )
            ):
                has_parent = True
                name_id = strat_name.id

                while has_parent:
                    # Get the parent of this unit

                    # Note: in PostgreSQL, the column `this_name` has been renamed to `parent`,
                    # and `that_name` has been renamed to `child`.
                    # Another note: there are only 3 entries in strat_tree where rel != 'parent', on 2025-12-17
                    res = db.run_query(
                        """
                        SELECT
                            parent, -- this_name has been renamed to parent
                            child,
                            strat_name,
                            strat_names.id,
                            rank
                        FROM macrostrat.strat_tree
                        JOIN macrostrat.strat_names
                          ON parent = strat_names.id
                        WHERE child = :child
                          AND rel = 'parent' and rank != ''
                        """,
                        dict(child=name_id),
                    ).all()

                    parent = None
                    if len(res) > 1:
                        # Warning: multiple parents found
                        snr = ",".join([str(r.parent) for r in res])
                        child = res[0].child
                        progress.console.print(
                            f"[yellow]Warning: multiple parents found; this may not be allowed. "
                            f"{child} > {snr}[/yellow]"
                        )
                    if len(res) > 0:
                        parent = res[0]

                    name_id = 0
                    parent_rank_id = None
                    parent_rank_name = None
                    if parent is not None:
                        name_id = parent.id
                        parent_rank_id = parent.rank.lower() + "_id"
                        parent_rank_name = parent.rank.lower() + "_name"

                    if name_id > 0:
                        db.run_query(
                            """
                            UPDATE macrostrat.lookup_strat_names_new
                            SET {parent_rank_id_col} = :parent_id, {parent_rank_name_col} = :parent_name
                            WHERE strat_name_id = :strat_name_id
                            """,
                            dict(
                                parent_rank_id_col=Identifier(parent_rank_id),
                                parent_rank_name_col=Identifier(parent_rank_name),
                                parent_id=parent.id,
                                parent_name=parent.strat_name,
                                strat_name_id=strat_name.id,
                            ),
                        )
                    else:
                        has_parent = False

                    _rank = strat_name.rank.lower()

                    sql = """
                    UPDATE macrostrat.lookup_strat_names_new SET t_units = (
                      SELECT COUNT(*)
                      FROM unit_strat_names
                      LEFT JOIN units_sections ON unit_strat_names.unit_id = units_sections.unit_id
                      LEFT JOIN cols ON units_sections.col_id = cols.id
                      WHERE unit_strat_names.strat_name_id IN (
                        SELECT strat_name_id
                        FROM lookup_strat_names
                        WHERE {rank_col} = :strat_name_id
                        AND rank::text = ANY(:strat_name_ranks)
                      )
                      AND cols.status_code = 'active'
                    )
                    WHERE strat_name_id = :strat_name_id
                    """

                    params = dict(
                        rank_col=Identifier(_rank + "_id"),
                        strat_name_id=strat_name.id,
                        strat_name_ranks=lookup_rank_children[_rank],
                    )

                    db.run_query(sql, params)
                    if i % 1000 == 0:
                        db.session.commit()

        db.session.commit()

    def part_2(self):
        db = get_database()

        # Populate `early_age` and `late_age`
        db.run_sql(
            """
            UPDATE macrostrat.lookup_strat_names_new lsn
            SET
                early_age = sub.early_age,
                late_age = sub.late_age
            FROM (
                SELECT strat_name_id, max(b_age) AS early_age, min(t_age) AS late_age
                FROM lookup_strat_names_new
                LEFT JOIN unit_strat_names USING (strat_name_id)
                LEFT JOIN lookup_unit_intervals USING (unit_id)
                GROUP BY strat_name_id
                ) AS sub
            WHERE lsn.strat_name_id = sub.strat_name_id
            """
        )
        db.session.commit()

        # Note: replaced mariadb substring_index with split_part for PostgreSQL
        # Populate rank_name
        # We have some python code to handle this now
        db.run_sql(
            """
            UPDATE lookup_strat_names_new SET rank_name = CASE
            WHEN split_part(strat_name, ' ', -1) IN ('Suite', 'Volcanics', 'Complex', 'Melange', 'Series', 'Supersuite', 'Tongue', 'Lens', 'Lentil', 'Drift', 'Metamorphics', 'Sequence', 'Supersequence', 'Intrusives', 'Measures', 'Division', 'Subsuite')
              THEN strat_name
            WHEN lower(split_part(strat_name, ' ', -1)) IN (SELECT lith FROM liths) AND rank = 'Fm'
              THEN strat_name
            WHEN lower(split_part(strat_name, ' ', -1)) = 'beds' AND rank = 'Bed'
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
            END;
            """
        )

        # Validate results
        res = db.run_query(
            """
            SELECT count(*) sn, (SELECT count(*) from lookup_strat_names_new) lsn
            FROM strat_names
            WHERE rank != ''
            """
        ).fetchone()
        n_rows = res.lsn
        if res.sn != n_rows:
            raise MacrostratError(
                "Inconsistent strat_name count in lookup table.",
                details=f"Found {n_rows} rows in lookup_strat_names_new",
            )

        db.run_sql(here / "sql" / "lookup-strat-names-02.sql")

        # alter table lookup_strat_names add column name_no_lith varchar(100);
        ### Remove lithological terms from strat names ###

        # Get a list of lithologies
        lith_results = db.run_query("SELECT lith FROM macrostrat.liths").fetchall()
        lithologies = [lith.lith for lith in lith_results]
        plural_lithologies = [lith + "s" for lith in lithologies]
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

        # Fetch all strat names
        strat_names = db.run_query(
            "SELECT strat_name_id, strat_name FROM lookup_strat_names_new"
        ).all()
        i = 0
        for strat_name in track(
            strat_names,
            description="Removing lithological terms...",
            total=len(strat_names),
        ):
            split_name = strat_name.strat_name.split(" ")

            name_no_lith = " ".join(
                [name for name in split_name if name.lower() not in lithologies]
            )
            db.run_query(
                """
                UPDATE macrostrat.lookup_strat_names_new
                SET name_no_lith = :name_no_lith
                WHERE strat_name_id = :strat_name_id
                """,
                dict(
                    name_no_lith=name_no_lith,
                    strat_name_id=strat_name.strat_name_id,
                ),
            )
            i += 1
            if i % 1000 == 0:
                db.session.commit()

        db.session.commit()

        db.run_sql(here / "sql" / "lookup-strat-names-03.sql")
