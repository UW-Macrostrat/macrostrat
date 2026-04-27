from psycopg2.sql import Identifier
from rich.progress import Progress

from macrostrat.cli.subsystems.rebuild.utils import (
    copy_table_into_place,
    here,
    update_intervals_lookup_units,
    update_timescale_lookup_units,
    update_timescale_unit_intervals,
    validate_counts,
)
from macrostrat.core.database import get_database
from macrostrat.core.exc import MacrostratError

# ---------------------------------------------------------------------------
# Scripts (unchanged logic, just consolidated)
# ---------------------------------------------------------------------------


def autocomplete():
    """autocomplete table"""
    db = get_database()
    db.run_sql(here / "sql" / "autocomplete.sql")


def unit_boundaries():
    """Unit boundaries and age model"""
    db = get_database()
    db.run_sql(here / "sql" / "unit-boundaries.sql")


def stats():
    """Project statistics"""
    db = get_database()
    db.run_sql(here / "sql" / "stats.sql")


def strat_name_footprints():
    """Footprints for stratigraphic names"""
    db = get_database()
    print("This create script takes 60m in prod and 23 min in development")
    db.run_sql(here / "sql" / "strat-name-footprints-01.sql")
    db.run_sql(here / "sql" / "strat-name-footprints-02.sql")


def lookup_units():
    """lookup_units table"""
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


def lookup_unit_intervals():
    """lookup_unit_intervals table"""
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


def lookup_unit_attrs_api():
    """Unit lithologies and attributes"""
    db = get_database()
    db.run_sql(here / "sql" / "lookup-unit-attrs-api-01.sql")
    validate_counts(db)
    copy_table_into_place(db, "lookup_unit_attrs_api")


class lookup_strat_names:
    """Stratigraphic names lookup table"""

    def __call__(self):
        """lookup_strat_names table"""
        # Allow this to emulate a function
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

        # Build full ancestor chain in one recursive query
        db.run_sql(
            """
            CREATE TEMP TABLE _ancestors AS
            WITH RECURSIVE tree AS (
                SELECT child AS strat_name_id, parent AS ancestor_id
                FROM macrostrat.strat_tree
                WHERE rel = 'parent'
                UNION ALL
                SELECT t.strat_name_id, st.parent
                FROM tree t
                JOIN macrostrat.strat_tree st ON st.child = t.ancestor_id AND st.rel = 'parent'
            )
            SELECT DISTINCT t.strat_name_id,
                sn.id AS ancestor_id,
                lower(sn.rank::text) AS ancestor_rank,
                sn.strat_name AS ancestor_name
            FROM tree t
            JOIN macrostrat.strat_names sn ON sn.id = t.ancestor_id AND sn.rank != '';

            CREATE INDEX ON _ancestors (strat_name_id);
            CREATE INDEX ON _ancestors (ancestor_rank);
        """
        )

        # Bulk update each rank column from the ancestor table
        for rank_lower in ["sgp", "gp", "subgp", "fm", "mbr", "bed"]:
            db.run_query(
                """
                UPDATE macrostrat.lookup_strat_names_new lsn
                SET {id_col} = a.ancestor_id, {name_col} = a.ancestor_name
                FROM _ancestors a
                WHERE a.strat_name_id = lsn.strat_name_id
                  AND a.ancestor_rank = :rank_lower
                """,
                dict(
                    rank_lower=rank_lower,
                    id_col=Identifier(rank_lower + "_id"),
                    name_col=Identifier(rank_lower + "_name"),
                ),
            )
            db.session.commit()

        # Bulk update t_units for all ranks at once
        rank_display = {
            "sgp": "SGp",
            "gp": "Gp",
            "subgp": "SubGp",
            "fm": "Fm",
            "mbr": "Mbr",
            "bed": "Bed",
        }

        for rank_lower, child_ranks in lookup_rank_children.items():
            db.run_query(
                """
                UPDATE macrostrat.lookup_strat_names_new lsn
                SET t_units = sub.cnt
                FROM (
                    SELECT lsn2.strat_name_id, COUNT(*) AS cnt
                    FROM macrostrat.lookup_strat_names_new lsn2
                    JOIN macrostrat.lookup_strat_names lsn_ref
                      ON lsn_ref.{rank_id_col} = lsn2.strat_name_id
                     AND lsn_ref.rank::text = ANY(:child_ranks)
                    JOIN macrostrat.unit_strat_names usn ON usn.strat_name_id = lsn_ref.strat_name_id
                    LEFT JOIN macrostrat.units_sections us ON us.unit_id = usn.unit_id
                    LEFT JOIN macrostrat.cols c ON c.id = us.col_id
                    WHERE lsn2.rank::text = :rank
                      AND (c.status_code = 'active')
                    GROUP BY lsn2.strat_name_id
                ) sub
                WHERE lsn.strat_name_id = sub.strat_name_id
                """,
                dict(
                    rank_id_col=Identifier(rank_lower + "_id"),
                    child_ranks=child_ranks,
                    rank=rank_display[rank_lower],
                ),
            )
            db.session.commit()

        db.run_sql("DROP TABLE IF EXISTS _ancestors;")
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

        db.run_query(
            """
            UPDATE macrostrat.lookup_strat_names_new
            SET name_no_lith = (
                SELECT string_agg(word, ' ' ORDER BY ord)
                FROM unnest(string_to_array(strat_name, ' ')) WITH ORDINALITY AS t(word, ord)
                WHERE lower(word) != ALL(:lithologies)
            )
            """,
            dict(lithologies=lithologies),
        )
        db.session.commit()

        db.run_sql(here / "sql" / "lookup-strat-names-03.sql")
