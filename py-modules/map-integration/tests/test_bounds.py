"""Tests for a map's boundary from its features (`create_bounds`).

Run against ``test_db_base``, which commits, with cleanup by unique ids.
"""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.geometry import create_bounds
from macrostrat.map_integration.utils.map_info import get_map_info

SOURCE_ID = 999001
SLUG = "test_bounds"

# Disjoint, so the union keeps two parts.
POLYGONS = [
    "POLYGON((0 0, 0 3, 3 3, 3 0, 0 0))",
    "POLYGON((5 0, 5 3, 8 3, 8 0, 5 0))",
]


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        _db.run_sql(
            """
            INSERT INTO maps.sources (source_id, slug, name, scale, status_code)
            VALUES (:source_id, :slug, 'Bounds test map', 'large', 'active')
            """,
            dict(source_id=SOURCE_ID, slug=SLUG),
        )
        for wkt in POLYGONS:
            _db.run_sql(
                """
                INSERT INTO maps.polygons (source_id, scale, geom)
                VALUES (:source_id, 'large', ST_GeomFromText(:wkt, 4326))
                """,
                dict(source_id=SOURCE_ID, wkt=wkt),
            )
        _db.session.commit()
        yield _db


def _bounds(db):
    return db.run_query(
        """
        SELECT ST_NumGeometries(a.geometry) AS n_parts, a.area_km,
               ST_Equals(s.rgeom, a.geometry) AS mirrored,
               ST_Equals(s.web_geom, ST_Envelope(a.geometry)) AS web_geom_ok
        FROM map_bounds.map_area a
        JOIN maps.sources s ON s.source_id = a.id
        WHERE a.id = :source_id
        """,
        dict(source_id=SOURCE_ID),
    ).one()


def test_bounds_from_polygons(db):
    assert create_bounds(db, get_map_info(db, SLUG))
    row = _bounds(db)
    assert row.n_parts == 2
    assert row.area_km > 0
    assert row.mirrored
    assert row.web_geom_ok
    opening = db.run_query(
        "SELECT operation FROM map_bounds.boundary_op"
        " WHERE source_id = :source_id AND position = 0",
        dict(source_id=SOURCE_ID),
    ).scalar()
    assert opening == "union"


def test_plain_union_is_recomputed(db):
    _add_polygon(db, "POLYGON((10 0, 10 3, 13 3, 13 0, 10 0))")
    assert create_bounds(db, get_map_info(db, SLUG))
    assert _bounds(db).n_parts == 3


def test_composed_boundary_is_kept(db):
    db.run_sql(
        "UPDATE map_bounds.boundary_op SET operation = 'world'"
        " WHERE source_id = :source_id AND position = 0",
        dict(source_id=SOURCE_ID),
    )
    _add_polygon(db, "POLYGON((20 0, 20 3, 23 3, 23 0, 20 0))")
    assert not create_bounds(db, get_map_info(db, SLUG))
    assert _bounds(db).n_parts == 3


def test_boundary_without_operations_is_kept(db):
    db.run_sql(
        "DELETE FROM map_bounds.boundary_op WHERE source_id = :source_id",
        dict(source_id=SOURCE_ID),
    )
    db.run_sql(
        "UPDATE maps.sources SET web_geom = NULL WHERE source_id = :source_id",
        dict(source_id=SOURCE_ID),
    )
    assert not create_bounds(db, get_map_info(db, SLUG))
    row = _bounds(db)
    assert row.n_parts == 3
    assert row.web_geom_ok


def _add_polygon(db, wkt):
    db.run_sql(
        """
        INSERT INTO maps.polygons (source_id, scale, geom)
        VALUES (:source_id, 'large', ST_GeomFromText(:wkt, 4326))
        """,
        dict(source_id=SOURCE_ID, wkt=wkt),
    )
