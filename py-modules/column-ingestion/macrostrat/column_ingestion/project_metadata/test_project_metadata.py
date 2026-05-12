from pathlib import Path
import polars as pl
from macrostrat.utils import get_logger
from xlsxwriter import Workbook

from ..query_helpers import get_liths_for_unit
from . import _column_metadata_importer

__here__ = Path(__file__).parent

from ..defs_provider import MacrostratMetadataPopulator, MacrostratDatabaseDataProvider


class TestProjectMetadata:
    def test_insert_project_metadata(self, db, test_db, tmp_path: Path):
        # Insert project ID 13 to align with the test data

        # Populate metadata (intervals, etc.) from the "live" Macrostrat database
        _provider = MacrostratDatabaseDataProvider(db)
        MacrostratMetadataPopulator(_provider, test_db).populate_all()

        # Temporarily make sections not required for units in order for tests to pass.
        # We do this in a better way in the other importer.
        test_db.run_sql(
            "ALTER TABLE macrostrat.units ALTER COLUMN section_id DROP NOT NULL"
        )
        # Drop the foreign key constraint on units
        test_db.run_sql(
            "ALTER TABLE macrostrat.units DROP CONSTRAINT units_sections_fk",
            raise_on_error=True,
        )
        test_db.session.commit()

        test_db.run_query(
            "INSERT INTO macrostrat.projects (id, slug, project, descrip, timescale_id) VALUES (:id, :slug, :project, :descrip, :timescale_id)",
            {
                "id": 13,
                "slug": "test-project",
                "project": "Test Project",
                "descrip": "Test Description",
                "timescale_id": 11,
            },
        )
        test_db.session.commit()

        test_excel_file = tmp_path / "test_excel_file.xlsx"
        assemble_test_excel_file(
            __here__ / "test_fixtures" / "macrostrat_import_v3_excerpt", test_excel_file
        )

        conn = test_db.session.connection().connection

        _column_metadata_importer(
            conn,
            test_excel_file,
            audit_dir=tmp_path / "audit",
            do_audit=True,
        )

    def test_unit_count(self, test_db):
        """Test that the correct number of units are inserted"""
        assert test_db.run_query("SELECT COUNT(*) FROM macrostrat.units").scalar() == 6

    def test_mazko_formation_liths(self, test_db):
        """Test that the 'Mazko Formation' has the correct lithologies"""
        # Get the unit_id of the Mazco Formation
        unit_id = test_db.run_query(
            "SELECT id FROM macrostrat.units WHERE strat_name = 'Mazko Formation'"
        ).scalar()
        assert unit_id is not None

        liths = get_liths_for_unit(test_db, unit_id)
        lith_names = {lith.name for lith in liths}
        assert lith_names == {"sandstone", "siltstone"}

        sandstone = next(filter(lambda x: x.name == "sandstone", liths))
        assert sandstone.dom == "dom"
        atts = {att.name for att in sandstone.attributes}
        assert atts == {"tabular", "thickly bedded", "cross-bedded"}

        siltstone = next(filter(lambda x: x.name == "siltstone", liths))
        atts = {att.name for att in siltstone.attributes}
        assert atts == {"flute casts"}


log = get_logger(__name__)


def assemble_test_excel_file(src: Path, out_path: Path) -> Path:
    """
    Test helper function to assemble an ingestible Excel file from a directory of TSV files.
    """

    # Read TSV files from directory and write into single Excel file

    assert src.is_dir()
    assert out_path.suffix == ".xlsx"
    assert out_path.exists() is False

    tsv_files = list(src.glob("*.tsv"))
    assert len(tsv_files) > 0

    with Workbook(out_path) as workbook:
        for f in tsv_files:
            df = pl.read_csv(f, separator="\t")
            sheet_name = f.stem
            log.info(f"Writing {sheet_name} to {out_path}")
            df.write_excel(workbook=workbook, worksheet=sheet_name)

    return out_path
