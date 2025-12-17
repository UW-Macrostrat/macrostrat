from pathlib import Path

from psycopg2.sql import Identifier

from macrostrat.core.exc import MacrostratError
from ..base import Base
from ...database import get_db

here = Path(__file__).parent


class LookupStratNames(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        db = get_db()
        db.run_sql(here / "sql" / "lookup-strat-names.sql")

        lookup_rank_children = {
            "sgp": ["SGp", "Gp", "SubGp", "Fm", "Mbr", "Bed"],
            "gp": ["Gp", "SubGp", "Fm", "Mbr", "Bed"],
            "subgp": ["SubGp", "Fm", "Mbr", "Bed"],
            "fm": ["Fm", "Mbr", "Bed"],
            "mbr": ["Mbr", "Bed"],
            "bed": ["Bed"],
        }

        db.run_sql("SET SEARCH_PATH TO macrostrat, public;")

        # Get all the strat names
        res = db.run_query(
            """
            SELECT *
            FROM strat_names
            WHERE rank != ''
            ORDER BY strat_name
            """
        )

        for strat_name in res:
            rank_id = strat_name["rank"] + "_id"
            rank_name = strat_name["rank"] + "_name"

            db.run_sql(
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
                VALUES (:ref_id, :concept_id, :strat_name_id, :strat_name, :rank, :rank_id, :rank_name)
                """,
                dict(
                    ref_id=strat_name["ref_id"],
                    concept_id=strat_name["concept_id"],
                    strat_name_id=strat_name["id"],
                    strat_name=strat_name["strat_name"],
                    rank=strat_name["rank"],
                    rank_id=strat_name["id"],
                    rank_name=strat_name["strat_name"],
                    rank_id_col=Identifier(rank_id),
                    rank_name_col=Identifier(rank_name),
                ),
            )
            db.session.commit()

            has_parent = True
            name_id = strat_name["id"]

            while has_parent:
                # Get the parent of this unit

                # Note: in PostgreSQL, the column `this_name` has been renamed to `parent`,
                # and `that_name` has been renamed to `child`.
                # Another note: there are only 3 entries in strat_tree where rel != 'parent', on 2025-12-17
                parent = db.run_query(
                    """
                    SELECT
                        parent, -- this_name has been renamed to parent
                        strat_name,
                        strat_names.id,
                        rank
                    FROM macrostrat.strat_tree
                    JOIN macrostrat.strat_names
                      ON parent = strat_names.id
                    WHERE child = :name
                      AND rel = 'parent' and rank != ''
                    """,
                    dict(name=name_id),
                ).fetchone()

                if parent is None:
                    # Sketchy null check, we should improve this...
                    name_id = 0
                else:
                    name_id = parent["id"]

                if name_id > 0 and parent is not None:
                    parent_rank_id = parent["rank"] + "_id"
                    parent_rank_name = parent["rank"] + "_name"
                    db.run_sql(
                        """
                        UPDATE macrostrat.lookup_strat_names_new
                        SET {parent_rank_id_col} = :parent_id, {parent_rank_name_col} = :parent_name
                        WHERE strat_name_id = :strat_name_id
                        """,
                        dict(
                            parent_rank_id_col=Identifier(parent_rank_id),
                            parent_rank_name=Identifier(parent_rank_name),
                            parent_id=parent["id"],
                            parent_name=parent["strat_name"],
                            strat_name_id=strat_name["id"],
                        ),
                    )

                else:
                    has_parent = False

                _rank = strat_name["rank"].lower()

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
                    AND rank = ANY (:strat_name_ranks)
                  )
                  AND cols.status_code = 'active'
                )
                WHERE strat_name_id = :strat_name_id
                """

                params = dict(
                    rank_col=Identifier(_rank + "_id"),
                    strat_name_id=strat_name["id"],
                    strat_name_ranks=lookup_rank_children[_rank],
                )

                db.run_sql(sql, params)
                db.session.commit()

        db.session.commit()

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
            UPDATE lookup_strat_names_new
            SET rank_name = CASE
            WHEN split_part(strat_name, ' ', -1) IN (
                'Suite', 'Volcanics', 'Complex', 'Melange', 'Series', 'Supersuite',
                'Tongue', 'Lens', 'Lentil', 'Drift', 'Metamorphics', 'Sequence',
                'Supersequence', 'Intrusives', 'Measures', 'Division', 'Subsuite'
            )
              THEN strat_name
            WHEN lower(split_part(strat_name, ' ', -1)) IN (SELECT lith FROM liths) AND rank = 'fm'
              THEN strat_name
            WHEN lower(split_part(strat_name, ' ', -1) = 'Beds' AND rank = 'Bed'
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
        n_rows = res["lsn"]
        if res["sn"] != n_rows:
            raise MacrostratError(
                "Inconsistent strat_name count in lookup table.",
                details=f"Found {n_rows} rows in lookup_strat_names_new",
            )

        db.run_sql(here / "sql" / "lookup-strat-names-02.sql")

        # alter table lookup_strat_names add column name_no_lith varchar(100);
        ### Remove lithological terms from strat names ###

        # Get a list of lithologies
        lith_results = db.run_query("SELECT lith FROM macrostrat.liths").fetchall()
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

        # Fetch all strat names
        res = db.run_query(
            "SELECT strat_name_id, strat_name FROM lookup_strat_names_new"
        )
        for strat_name in res.fetchall():
            split_name = strat_name["strat_name"].split(" ")

            name_no_lith = " ".join(
                [name for name in split_name if name.lower() not in lithologies]
            )
            print(strat_name["strat_name_id"], name_no_lith)
            db.run_query(
                """
                UPDATE macrostrat.lookup_strat_names_new
                SET name_no_lith = :name_no_lith
                WHERE strat_name_id = :strat_name_id
                """,
                dict(
                    name_no_lith=name_no_lith,
                    strat_name_id=strat_name["strat_name_id"],
                ),
            )
            db.session.commit()

        db.session.commit()

        db.run_sql(here / "sql" / "lookup-strat-names-03.sql")
