"""Tests for references and the `col_refs` links."""

from pytest import raises

from macrostrat.column_ingestion.ingest import ingest_columns_from_file
from macrostrat.column_ingestion.refs import (
    Reference,
    ReferenceError,
    compose_citation,
    parse_ref_ids,
    reconcile_references,
)

# --- pure -------------------------------------------------------------------------


def test_citation_joins_title_and_publication():
    assert compose_citation("A study of rocks", "Journal of Rocks") == (
        "A study of rocks. Journal of Rocks"
    )


def test_citation_omits_a_missing_publication():
    assert compose_citation("A study of rocks", None) == "A study of rocks"
    assert compose_citation("A study of rocks", "   ") == "A study of rocks"


def test_ref_ids_split_on_commas():
    assert parse_ref_ids("10, 20") == ["10", "20"]
    assert parse_ref_ids("11") == ["11"]
    assert parse_ref_ids(None) == []
    assert parse_ref_ids("") == []


# --- against the fixture workbook -------------------------------------------------


class TestIngestedReferences:
    def test_references_are_written(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)

        rows = db.run_query(
            """
            SELECT pub_year, author, ref FROM macrostrat.refs
            WHERE id <> 217 ORDER BY id
            """
        ).fetchall()

        assert rows, "the workbook's refs sheet was ingested"
        assert all(r.pub_year > 1800 for r in rows), "a real publication year"
        assert all(r.author and r.ref for r in rows), "NOT NULL fields are populated"

    def test_columns_are_linked_to_the_refs_they_cite(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)

        linked = db.run_query(
            """
            SELECT c.col_name, count(cr.ref_id) n_refs
            FROM macrostrat.cols c
            LEFT JOIN macrostrat.col_refs cr ON cr.col_id = c.id
            GROUP BY c.col_name ORDER BY c.col_name
            """
        ).fetchall()

        assert linked, "columns were written"
        assert all(r.n_refs > 0 for r in linked), "every column cites at least one ref"
        # The workbook cites several columns against two refs ("10, 20").
        assert any(r.n_refs > 1 for r in linked)

    def test_reference_reuse_rather_than_duplication(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        """`refs` is shared across projects, so a citation already present is reused."""
        ingest_columns_from_file(db, excel_file)
        first = db.run_query("SELECT count(*) FROM macrostrat.refs").scalar()

        ingest_columns_from_file(db, excel_file)
        second = db.run_query("SELECT count(*) FROM macrostrat.refs").scalar()

        assert second == first, "a re-import must not duplicate references"

    def test_reference_ids_are_stable_across_reimport(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)
        before = [
            r[0]
            for r in db.run_query(
                "SELECT id FROM macrostrat.refs ORDER BY id"
            ).fetchall()
        ]

        ingest_columns_from_file(db, excel_file)
        after = [
            r[0]
            for r in db.run_query(
                "SELECT id FROM macrostrat.refs ORDER BY id"
            ).fetchall()
        ]

        assert after == before
        links = db.run_query("SELECT count(*) FROM macrostrat.col_refs").scalar()
        assert links > 0, "links survive too"


class TestReferenceReuseAcrossProjects:
    def test_an_existing_citation_is_matched_not_reinserted(self, db):
        """The natural key is the citation, not the project, so an import finds a
        reference another project already contributed."""
        reference = Reference(
            local_id="1",
            pub_year=2002,
            author="Geocentre",
            ref="A legend. VSEGEI",
        )

        first = reconcile_references(db, [reference])
        db.session.commit()
        second = reconcile_references(db, [reference])

        assert first == second, "the same citation resolves to the same row"
        assert (
            db.run_query(
                "SELECT count(*) FROM macrostrat.refs WHERE author = 'Geocentre'"
            ).scalar()
            == 1
        )


class TestReferenceValidation:
    def test_unknown_ref_ids_are_reported(
        self, db, test_project, default_age_model_ref, excel_file, tmp_path
    ):
        """A column citing a ref_id absent from the refs sheet is an error naming the
        column, not a silently dropped link."""
        from macrostrat.column_ingestion.refs import resolve_column_references

        class FakeColumn:
            id = 1
            local_id = "9999"
            name = "New Shanan"
            ref_ids = ["11", "does-not-exist"]

        with raises(ReferenceError) as err:
            resolve_column_references(db, [FakeColumn()], {"11": 1})

        assert "does-not-exist" in str(err.value)
        assert "9999" in str(err.value)
