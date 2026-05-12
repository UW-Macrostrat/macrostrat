from pathlib import Path
from uuid import uuid4

import polars as pl
from pytest import fixture
from xlsxwriter import Workbook

from macrostrat.core.database.sequences import reset_sequence
from macrostrat.database import Database, create_database, drop_database
from macrostrat.utils import get_logger

from ..ingest import ingest_columns_from_file
from ..query_helpers import get_liths_for_unit
from . import _column_metadata_importer

__here__ = Path(__file__).parent

from ..defs_provider import MacrostratDatabaseDataProvider, MacrostratMetadataPopulator


@fixture(scope="class")
def db(test_db_macrostrat_schema_only: Database):
    """A new test database created from a template of the test database and dropped afterwards.
    We use this pattern to ensure that we have a clean database for each test where isolation
    (beyond transaction isolation) is required.
    """
    db = test_db_macrostrat_schema_only
    uid = str(uuid4())[:8]
    db_name = db.engine.url.database
    template_db_name = db_name + "_template_" + uid
    # Close connection to the database so we can create a new one based on the template
    new_db_url = db.engine.url.set(database=template_db_name)
    db.session.close()
    db.engine.dispose()
    create_database(new_db_url, template=db_name)
    yield Database(new_db_url)
    drop_database(new_db_url)


class TestProjectMetadata:
    def test_insert_project_metadata(self, env_db, db, tmp_path: Path):
        # Insert project ID 13 to align with the test data

        # Populate metadata (intervals, etc.) from the "live" Macrostrat database
        _provider = MacrostratDatabaseDataProvider(env_db)
        MacrostratMetadataPopulator(_provider, db).populate_all()

        # Temporarily make sections not required for units in order for tests to pass.
        # We do this in a better way in the other importer.
        db.run_sql("ALTER TABLE macrostrat.units ALTER COLUMN section_id DROP NOT NULL")
        # Drop the foreign key constraint on units
        db.run_sql(
            "ALTER TABLE macrostrat.units DROP CONSTRAINT units_sections_fk",
            raise_on_error=True,
        )
        db.session.commit()

        db.run_query(
            "INSERT INTO macrostrat.projects (id, slug, project, descrip, timescale_id) VALUES (:id, :slug, :project, :descrip, :timescale_id)",
            {
                "id": 13,
                "slug": "test-project",
                "project": "Test Project",
                "descrip": "Test Description",
                "timescale_id": 11,
            },
        )
        db.session.commit()

        test_excel_file = tmp_path / "test_excel_file.xlsx"
        assemble_test_excel_file(
            __here__ / "test_fixtures" / "macrostrat_import_v3_excerpt", test_excel_file
        )

        conn = db.session.connection().connection

        _column_metadata_importer(
            conn,
            test_excel_file,
            audit_dir=tmp_path / "audit",
            do_audit=True,
        )

        # TODO: write artifacts somewhere we can see them

    def test_unit_count(self, db):
        """Test that the correct number of units are inserted"""
        assert db.run_query("SELECT COUNT(*) FROM macrostrat.units").scalar() == 6

    def test_lithologies(self, db):
        """Test that the correct lithologies are inserted"""
        _test_mazko_formation_liths(db)


def _test_mazko_formation_liths(db):
    """Test that the 'Mazko Formation' has the correct lithologies"""
    # Get the unit_id of the Mazco Formation
    unit_id = db.run_query(
        "SELECT id FROM macrostrat.units WHERE strat_name = 'Mazko Formation'"
    ).scalar()
    assert unit_id is not None

    liths = get_liths_for_unit(db, unit_id)
    lith_names = {lith.name for lith in liths}
    assert lith_names == {"sandstone", "siltstone"}

    sandstone = next(filter(lambda x: x.name == "sandstone", liths))
    assert sandstone.dom == "dom"
    atts = {att.name for att in sandstone.attributes or {}}
    assert atts == {"tabular", "thickly bedded", "cross-bedded"}

    siltstone = next(filter(lambda x: x.name == "siltstone", liths))
    atts = {att.name for att in siltstone.attributes or {}}
    assert atts == {"flute casts"}


class TestStandardImportProcess:
    def test_insert_project_metadata(self, env_db, db, tmp_path: Path):
        _provider = MacrostratDatabaseDataProvider(env_db)
        MacrostratMetadataPopulator(_provider, db).populate_all()

        # Temporarily make sections not required for units in order for tests to pass.
        # We do this in a better way in the other importer.
        db.run_sql("ALTER TABLE macrostrat.units ALTER COLUMN section_id DROP NOT NULL")
        # Drop the foreign key constraint on units
        db.run_sql(
            "ALTER TABLE macrostrat.units DROP CONSTRAINT units_sections_fk",
            raise_on_error=True,
        )
        db.session.commit()

        # TODO: this shares state with the previous test, but we should fix that
        db.run_query(
            "INSERT INTO macrostrat.projects (id, slug, project, descrip, timescale_id) VALUES (:id, :slug, :project, :descrip, :timescale_id)",
            {
                "id": 13,
                "slug": "test-project",
                "project": "Test Project",
                "descrip": "Test Description",
                "timescale_id": 11,
            },
        )
        db.session.commit()

        test_excel_file = tmp_path / "test_excel_file.xlsx"
        assemble_test_excel_file(
            __here__ / "test_fixtures" / "macrostrat_import_v3_excerpt", test_excel_file
        )

        # We need to insert Macrostrat's default age model as a reference with ID=217
        db.run_sql(
            "INSERT INTO macrostrat.refs (id, pub_year, author, ref, compilation_code) VALUES (217, 2021, 'Peters, S.E. et al.', 'Macrostrat default age model', '')",
            raise_on_error=True,
        )
        db.session.commit()
        # Ensure that the sequence is reset so that future inserts will not conflict with the manually inserted reference
        reset_sequence(db, "macrostrat.refs", "id")
        db.session.commit()

        ingest_columns_from_file(
            db,
            test_excel_file,
        )

    def test_unit_count(self, db):
        """Test that the correct number of units are inserted"""
        assert db.run_query("SELECT COUNT(*) FROM macrostrat.units").scalar() == 6

    def test_lithologies(self, db):
        """Test that the correct lithologies are inserted"""
        _test_mazko_formation_liths(db)


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
