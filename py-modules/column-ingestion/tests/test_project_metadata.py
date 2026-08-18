"""Tests for the two importers: Shanan's legacy project-metadata path, and ours.

Shared fixtures (`db`, `excel_file`, `test_project`, `default_age_model_ref`) come from
`conftest.py`.
"""

from pathlib import Path

from macrostrat.column_ingestion.ingest import ingest_columns_from_file
from macrostrat.column_ingestion.project_metadata import _column_metadata_importer
from macrostrat.column_ingestion.query_helpers import get_liths_for_unit
from macrostrat.utils import get_logger

log = get_logger(__name__)


def assert_mazko_formation_liths(db):
    """The 'Mazko Formation' should carry the lithologies its workbook row describes."""
    unit_id = db.run_query(
        "SELECT id FROM macrostrat.units WHERE strat_name = 'Mazko Formation'"
    ).scalar()
    assert unit_id is not None

    liths = get_liths_for_unit(db, unit_id)
    assert {lith.name for lith in liths} == {"sandstone", "siltstone"}

    sandstone = next(filter(lambda x: x.name == "sandstone", liths))
    assert sandstone.dom == "dom"
    assert {att.name for att in sandstone.attributes or {}} == {
        "tabular",
        "thickly bedded",
        "cross-bedded",
    }

    siltstone = next(filter(lambda x: x.name == "siltstone", liths))
    assert {att.name for att in siltstone.attributes or {}} == {"flute casts"}


class TestLegacyProjectMetadataImporter:
    """The 2,794-line importer kept for reference. Requires the schema to be relaxed —
    it cannot precalculate sections, so it has to insert units before they exist. See
    `Investigations/Project metadata importer.md`."""

    def test_insert_project_metadata(
        self, db, test_project, excel_file, tmp_path: Path
    ):
        db.run_sql("ALTER TABLE macrostrat.units ALTER COLUMN section_id DROP NOT NULL")
        db.run_sql(
            "ALTER TABLE macrostrat.units DROP CONSTRAINT units_sections_fk",
            raise_on_error=True,
        )
        db.session.commit()

        _column_metadata_importer(
            db.session.connection().connection,
            excel_file,
            audit_dir=tmp_path / "audit",
            do_audit=True,
        )

        assert db.run_query("SELECT COUNT(*) FROM macrostrat.units").scalar() == 6
        assert_mazko_formation_liths(db)


class TestStandardImportProcess:
    """Our importer, which satisfies the schema as it stands."""

    def test_insert_project_metadata(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)

        assert db.run_query("SELECT COUNT(*) FROM macrostrat.units").scalar() == 6
        assert_mazko_formation_liths(db)


class TestReimportPreservesIdentity:
    """Re-importing the same workbook must not churn rows.

    `write_units` used to delete every unit for a (column, section) and re-insert.
    Because `unit_liths`, `unit_boundaries` and friends reference `units.id` with
    `ON DELETE CASCADE`, that silently destroyed the age model built from the same
    workbook on every re-run.
    """

    def _snapshot(self, db):
        def ids(table):
            return [
                r[0]
                for r in db.run_query(f"SELECT id FROM {table} ORDER BY id").fetchall()
            ]

        def count(table):
            return db.run_query(f"SELECT count(*) FROM {table}").scalar()

        return {
            "refs": ids("macrostrat.refs"),
            "col_refs": ids("macrostrat.col_refs"),
            "cols": ids("macrostrat.cols"),
            "sections": ids("macrostrat.sections"),
            "units": ids("macrostrat.units"),
            "liths": count("macrostrat.unit_liths"),
            "lith_atts": count("macrostrat.unit_liths_atts"),
            "units_sections": count("macrostrat.units_sections"),
            "environs": count("macrostrat.unit_environs"),
            "notes": count("macrostrat.unit_notes"),
            "boundaries": count("macrostrat.unit_boundaries"),
        }

    def test_second_ingest_is_stable(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)
        first = self._snapshot(db)
        assert len(first["units"]) == 6
        assert first["liths"] > 0, "first import should write lithologies"
        assert first["boundaries"] > 0, "first import should build an age model"

        ingest_columns_from_file(db, excel_file)
        second = self._snapshot(db)

        assert second["units"] == first["units"], (
            "unit ids must survive a re-import; new ids mean the rows were deleted and "
            "recreated, cascading through everything that references them"
        )
        assert second["cols"] == first["cols"], "column ids must survive a re-import"
        assert second["refs"] == first["refs"], "reference ids likewise"
        assert second["col_refs"] == first["col_refs"], "and their column links"
        assert second["sections"] == first["sections"], "section ids likewise"
        assert second["liths"] == first["liths"], "unit_liths must not accumulate"
        assert second["lith_atts"] == first["lith_atts"]
        assert second["units_sections"] == first["units_sections"]
        assert second["environs"] == first["environs"]
        assert second["notes"] == first["notes"]
        assert second["boundaries"] == first["boundaries"]

        assert_mazko_formation_liths(db)
