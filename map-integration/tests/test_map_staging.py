from psycopg2.sql import Identifier
from macrostrat.map_integration.commands.ingest import ingest_map
from macrostrat.map_integration.utils.map_info import get_map_info
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.commands.prepare_fields import _prepare_fields
from macrostrat.map_integration.utils.file_discovery import find_gis_files
from pathlib import Path
import pytest



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


@pytest.fixture
def test_maps():
    return {
        "slug": "test_map",
        "data_path": Path(__file__).parent / "fixtures" / "maps" / "Itaete",
        "name": "Test Map",
        "scale": "large",
        "object_group_id": 1,
        "filter": None,
    }




def test_map_staging(db, test_maps):
    """
    Ingest a map, update metadata, prepare fields, and build geometries.
    """
    slug = test_maps["slug"]
    data_path = test_maps["data_path"]
    name = test_maps["name"]
    scale = test_maps["scale"]
    object_group_id = test_maps["object_group_id"]
    filter = test_maps["filter"]

    slug = slug.lower().replace(" ", "_")
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
        "SELECT source_id FROM maps.sources_metadata WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()

    if source_id is None:
        raise RuntimeError(f"Could not find source for slug {slug}")

    if name:
        db.run_sql(
            "UPDATE maps.sources_metadata SET name = :name WHERE source_id = :source_id",
            dict(name=name, source_id=source_id),
        )
    if scale:
        db.run_sql(
            "UPDATE maps.sources_metadata SET scale = :scale WHERE source_id = :source_id",
            dict(scale=scale, source_id=source_id),
        )

    db.run_sql(
        """
        INSERT INTO maps_metadata.ingest_process (state, source_id, object_group_id)
        VALUES ('ingested', :source_id, :object_group_id)
        """,
        dict(source_id=source_id, object_group_id=object_group_id),
    )

    map_info = get_map_info(db, slug)
    _prepare_fields(map_info)
    create_rgeom(map_info)
    create_webgeom(map_info)

    #Metadata assertions
    row = db.run_query(
        "SELECT name, scale FROM maps.sources_metadata WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    assert row is not None
    assert row.name == name
    assert row.scale == scale

    #Ingest process assertions
    ingest_process = db.run_query(
        "SELECT state, object_group_id FROM maps_metadata.ingest_process WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    assert ingest_process is not None
    assert ingest_process.state == "ingested"
    assert ingest_process.object_group_id == object_group_id

    #Geometry column assertions
    cols = db.run_query(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'sources' AND table_name = :table
        """,
        dict(table=f"{slug}_polygons"),
    ).scalars()
    assert "rgeom" in cols
    assert "webgeom" in cols

    #Data exists
    count = db.run_query(
        f"SELECT COUNT(*) FROM sources.{slug}_polygons"
    ).scalar()
    assert count > 0


