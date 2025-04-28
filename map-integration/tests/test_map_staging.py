from pathlib import Path

import pytest
from psycopg2.sql import Identifier
from sqlalchemy import create_engine, text

from macrostrat.core.database import Database
from macrostrat.map_integration.commands.ingest import ingest_map
from macrostrat.map_integration.commands.prepare_fields import _prepare_fields
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.file_discovery import find_gis_files
from macrostrat.map_integration.utils.map_info import get_map_info


def test_maps_tables_exist(db):
    """Test that the tables exist in the database."""
    for table in ["polygons", "lines", "points"]:
        res = db.run_query(
            "SELECT * FROM {table}", dict(table=Identifier("maps", table))
        ).all()
        assert len(res) == 0


def test_get_database(db):
    from macrostrat.core.database import db_ctx

    db_ctx.set(db)
    from macrostrat.map_integration.database import get_database

    db1 = get_database()
    assert db1 is db


"""
@pytest.fixture(scope="session", autouse=True)
def allow_macrostrat_login():
    super_engine = create_engine("postgresql://postgres@localhost:54884/postgres?sslmode=disable")
    with super_engine.connect() as conn:
        conn.execute(text("ALTER ROLE macrostrat LOGIN"))
        conn.commit()



@pytest.fixture
def db_as_macrostrat(allow_macrostrat_login):
    # Adjust to match your test DB port
    url = "postgresql://macrostrat@localhost:54884/macrostrat?sslmode=disable"
    engine = create_engine(url)
    db = Database(engine)
    yield db
    engine.dispose()"""


@pytest.fixture
def test_maps():
    return {
        "slug": "test_map",
        "data_path": Path(__file__).parent / "fixtures" / "maps" / "Itaete",
        "name": "Test Map",
        "scale": "large",
        "filter": None,
    }


def test_map_staging(db, test_maps):
    """
    Ingest a map, update metadata, prepare fields, and build geometries.
    """
    # db = db_as_macrostrat
    slug = test_maps["slug"]
    data_path = test_maps["data_path"]
    name = test_maps["name"]
    scale = test_maps["scale"]
    filter = test_maps["filter"]

    print(f"Ingesting {slug} from {data_path}")

    gis_files, excluded_files = find_gis_files(Path(data_path), filter=filter)
    if not gis_files:
        raise ValueError(f"No GIS files found in {data_path}")

    print(f"Found {len(gis_files)} GIS file(s)")
    for path in gis_files:
        print(f"  ✓ {path}")

    if excluded_files:
        print(f"Excluded {len(excluded_files)} file(s) due to filter:")
        for path in excluded_files:
            print(f"  ⚠️ {path}")

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
    if scale:
        db.run_sql(
            "UPDATE maps.sources SET scale = :scale WHERE source_id = :source_id",
            dict(scale=scale, source_id=source_id),
        )

    # object_group_id is a foreign key into the storage schema where the curr user postgres does not have access to.
    # the storage.sql ALTER TABLE storage.object OWNER TO macrostrat is switching the owner.
    # we are temporarily using macrostrat to run the query below
    object_group_id = db.run_query(
        "INSERT INTO storage.object_group DEFAULT VALUES RETURNING id"
    ).scalar()

    assert object_group_id is not None

    db.run_sql(
        """
        INSERT INTO maps_metadata.ingest_process (state, source_id, object_group_id)
        VALUES (:state, :source_id, :object_group_id);
        """,
        dict(state="ingested", source_id=source_id, object_group_id=object_group_id),
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
    assert row.scale == scale

    # Ingest process assertions
    ingest_process = db.run_query(
        "SELECT source_id, object_group_id, state FROM maps_metadata.ingest_process WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    assert ingest_process is not None
    assert ingest_process.state == "ingested"
    assert ingest_process.object_group_id == object_group_id

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

    print("All tests have passed the map ingestion staging test suite!")
