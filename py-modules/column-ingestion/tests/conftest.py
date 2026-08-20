from pathlib import Path

import polars as pl
from pytest import fixture
from xlsxwriter import Workbook

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.utils import get_logger

log = get_logger(__name__)

FIXTURES = Path(__file__).parent / "fixtures"


@fixture(scope="class")
def db(test_db_macrostrat_schema_only: Database, env_db: Database):
    """A fresh database per test class, templated from the schema-only test database.

    Used where isolation beyond transaction rollback is required.
    """
    log.info("Setting up template database")
    with template_database(
        test_db_macrostrat_schema_only, close_source_connections=True
    ) as engine:
        yield Database(engine)


def assemble_test_excel_file(src: Path, out_path: Path) -> Path:
    """Assemble an ingestible Excel workbook from a directory of TSV files."""
    assert src.is_dir()
    assert out_path.suffix == ".xlsx"
    assert out_path.exists() is False

    tsv_files = list(src.glob("*.tsv"))
    assert len(tsv_files) > 0

    with Workbook(out_path) as workbook:
        for f in tsv_files:
            df = pl.read_csv(f, separator="\t")
            log.info(f"Writing {f.stem} to {out_path}")
            df.write_excel(workbook=workbook, worksheet=f.stem)

    return out_path


@fixture
def excel_file(tmp_path: Path) -> Path:
    """The v3 excerpt workbook, assembled into a temporary .xlsx."""
    return assemble_test_excel_file(
        FIXTURES / "macrostrat_import_v3_excerpt", tmp_path / "test_excel_file.xlsx"
    )


@fixture(scope="class")
def test_project(db):
    """Project 13, which the fixture workbook's metadata refers to."""
    db.run_query(
        "INSERT INTO macrostrat.projects (id, slug, project, descrip, timescale_id)"
        " VALUES (:id, :slug, :project, :descrip, :timescale_id)",
        {
            "id": 13,
            "slug": "test-project",
            "project": "Test Project",
            "descrip": "Test Description",
            "timescale_id": 11,
        },
    )
    db.session.commit()
    return 13


@fixture(scope="class")
def default_age_model_ref(db):
    """`unit_boundaries.ref_id` defaults to 217, Macrostrat's default age model."""
    from macrostrat.database import reset_sequence

    db.run_sql(
        "INSERT INTO macrostrat.refs (id, pub_year, author, ref, compilation_code)"
        " VALUES (217, 2021, 'Peters, S.E. et al.',"
        " 'Macrostrat default age model', '')",
        raise_on_error=True,
    )
    db.session.commit()
    reset_sequence(db, "macrostrat.refs", "id")
    db.session.commit()
