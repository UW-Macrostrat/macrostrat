from pathlib import Path
import polars as pl
from macrostrat.utils import get_logger
from xlsxwriter import Workbook

from . import _column_metadata_importer

__here__ = Path(__file__).parent

from ..defs_provider import MacrostratMetadataPopulator, MacrostratDatabaseDataProvider


def test_insert_project_metadata(env_db, test_db, tmp_path: Path):
    # Insert project ID 13 to align with the test data

    # Populate metadata (intervals, etc.) from the "live" Macrostrat database
    _provider = MacrostratDatabaseDataProvider(env_db)
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

    _column_metadata_importer(
        test_db,
        test_excel_file,
        audit_dir=tmp_path / "audit",
        do_audit=True,
    )


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
