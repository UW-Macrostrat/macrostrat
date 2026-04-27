from pathlib import Path

import pytest
from contextlib import contextmanager
from psycopg2.sql import Identifier

from macrostrat.map_integration.commands.ingest import ingest_map
from macrostrat.map_integration.commands.prepare_fields import _prepare_fields
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.ingestion_utils import find_gis_files
from macrostrat.map_integration.utils.map_info import get_map_info


def test_maps_tables_exist(test_db):
    """Test that the tables exist in the database."""
    db = test_db

    for table in ["polygons", "lines", "points"]:
        res = db.run_query(
            "SELECT * FROM {table}", dict(table=Identifier("maps", table))
        ).all()
        assert len(res) == 0


def test_get_database(test_db):
    from macrostrat.core.database import db_ctx

    db = test_db

    db_ctx.set(db)
    from macrostrat.map_integration.database import get_database

    db1 = get_database()
    assert db1 is db


__fixtures__ = Path(__file__).parent / "fixtures" / "maps"

from shutil import unpack_archive
from tempfile import TemporaryDirectory


japan_map_files = (__fixtures__).glob("*.zip")

ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tar.bz2", ".tgz")


@contextmanager
def extracted_path(path: Path):
    """If needed, unzips test data to temporary directories for working with on import"""
    # Unzip the files to temporary directories, and yield temporary paths
    if path.is_file() and path.suffix in ARCHIVE_SUFFIXES:
        with TemporaryDirectory() as tmpdir:
            unpack_archive(path, tmpdir)
            yield Path(tmpdir)
    else:
        yield path


@pytest.mark.parametrize("region_path", japan_map_files)
def test_map_staging(test_db, region_path):
    """
    Ingest a map, update metadata, prepare fields, and build geometries.
    """
    db = test_db
    slug = f"test_{region_path.stem.lower()}"
    name = region_path.stem
    data_path = region_path
    print(f"\n🚀 Ingesting map for region: {name} at {data_path}")

    with extracted_path(data_path) as data_path:
        gis_files, excluded_files = find_gis_files(data_path)
        assert gis_files, f"No GIS files found for {region_path}"

        for path in gis_files:
            print(f"  ✓ {path}")

        # Ingest
        ingest_map(slug, gis_files, if_exists="replace")

    source_id = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()

    if source_id is None:
        raise RuntimeError(f"Could not find source for slug {slug}")

    if name:
        db.run_sql(
            "UPDATE maps.sources SET name = :name WHERE source_id = :source_id",
            dict(name=name, source_id=source_id),
        )

    db.run_sql(
        "UPDATE maps.sources SET scale = :scale WHERE source_id = :source_id",
        dict(scale="large", source_id=source_id),
    )

    db.run_sql(
        """
        INSERT INTO maps_metadata.ingest_process (state, source_id)
        VALUES (:state, :source_id);
        """,
        dict(state="ingested", source_id=source_id),
    )

    map_info = get_map_info(db, slug)
    _prepare_fields(map_info)
    create_rgeom(map_info)
    create_webgeom(map_info)

    # Metadata assertions
    row = db.run_query(
        "SELECT name, scale FROM maps.sources WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    assert row is not None
    assert row.name == name
    assert row.scale == "large"

    # Ingest process assertions
    ingest_process = db.run_query(
        "SELECT source_id, state FROM maps_metadata.ingest_process WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    assert ingest_process is not None
    assert ingest_process.state == "ingested"

    # Data exists
    count = db.run_query(f"SELECT COUNT(*) FROM sources.{slug}_polygons").scalar()
    assert count > 0

    # Geometry column assertions
    rgeom = db.run_query(
        """
        SELECT rgeom FROM maps.sources WHERE slug = :slug
        """,
        dict(slug=slug),
    ).fetchone()
    assert rgeom is not None

    web_geom = db.run_query(
        """
        SELECT web_geom FROM maps.sources WHERE slug = :slug
        """,
        dict(slug=slug),
    ).fetchone()
    assert web_geom is not None

    print(f"✅ {region_path.name} passed the map ingestion staging test suite!\n")
