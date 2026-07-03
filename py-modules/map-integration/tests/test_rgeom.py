"""Tests for reference-geometry (rgeom) creation.

These run against ``test_db_base`` rather than ``test_db_full``: ``create_rgeom``
runs its ``basic.sql`` step inside ``db.transaction()``, which opens a *fresh*
engine connection. Under the rollback-wrapped ``test_db_full`` fixture that
connection can't see the test's uncommitted setup data, so we use the
non-rollback ``test_db_base`` (which commits) and clean up after ourselves.
"""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.geometry import create_rgeom
from macrostrat.map_integration.utils.map_info import get_map_info

# A high source_id unlikely to collide with anything in the test database.
TEST_SOURCE_ID = 999001
TEST_SLUG = "test_rgeom_basic"

# Two *disjoint* polygons (so their union is a MULTIPOLYGON), each with an
# interior ring (hole). With ``buffer=0`` nothing dissolves the parts into a
# single polygon, so this is exactly the path that used to raise
# "Failed at filling interior": ``ST_ExteriorRing(<MULTIPOLYGON>)`` is NULL.
TEST_POLYGONS = [
    "POLYGON((0 0, 0 3, 3 3, 3 0, 0 0),(1 1, 1 2, 2 2, 2 1, 1 1))",
    "POLYGON((5 0, 5 3, 8 3, 8 0, 5 0),(6 1, 6 2, 7 2, 7 1, 6 1))",
]


@pytest.fixture(scope="session")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        add_test_data(_db)
        yield _db


def add_test_data(db):
    """Populate a map with a few polygons in the maps schema plus a placeholder
    ``map_bounds.map_area`` row, and bind it as the active database so
    ``create_rgeom`` (which calls ``get_database()``) resolves to it.
    """

    # create_rgeom() resolves its database via get_database() -> db_ctx.

    # primary_table is unused on the maps.polygons path, but create_rgeom builds
    # Identifier("sources", primary_table) eagerly, which rejects NULL — so set it.
    db.run_sql(
        """
        INSERT INTO maps.sources
            (source_id, slug, name, primary_table, scale, status_code, is_finalized)
        VALUES (:source_id, :slug, 'RGeom test map', :primary_table, 'large', 'active', true)
        """,
        dict(
            source_id=TEST_SOURCE_ID,
            slug=TEST_SLUG,
            primary_table=f"{TEST_SLUG}_polygons",
        ),
    )

    for wkt in TEST_POLYGONS:
        db.run_sql(
            """
            INSERT INTO maps.polygons (source_id, scale, geom)
            VALUES (:source_id, 'large', ST_GeomFromText(:wkt, 4326))
            """,
            dict(source_id=TEST_SOURCE_ID, wkt=wkt),
        )

    # basic.sql UPDATEs an existing map_area row (normally created by
    # map-topology's copy-all-maps.sql). geometry is NOT NULL, so seed a
    # placeholder for the UPDATE to overwrite.
    db.run_sql(
        """
        INSERT INTO map_bounds.map_area (id, geometry)
        VALUES (:source_id, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326)))
        """,
        dict(source_id=TEST_SOURCE_ID),
    )

    db.session.commit()


def test_create_rgeom_basic_fills_holes_without_buffer(db):
    """The default path (buffer=0, fill_holes=True) over a multipolygon should
    succeed and remove interior rings. Regression test: this used to raise
    "Failed at filling interior" because ST_ExteriorRing returns NULL for a
    MULTIPOLYGON.
    """
    map_info = get_map_info(db, TEST_SLUG)

    assert map_info.id == TEST_SOURCE_ID

    create_rgeom(map_info, fill_holes=True, use_maps_schema=True, database=db)

    # Step 1 (union) populates maps.sources.rgeom with both disjoint parts.
    rgeom = db.run_query(
        """
        SELECT ST_IsValid(rgeom) AS valid, ST_NumGeometries(rgeom) AS n_parts
        FROM maps.sources WHERE source_id = :source_id
        """,
        dict(source_id=TEST_SOURCE_ID),
    ).one()
    assert rgeom.valid
    assert rgeom.n_parts == 2

    # Step 2 (basic.sql) writes the processed geometry to map_bounds.map_area,
    # with all interior rings removed.
    area = db.run_query(
        """
        SELECT
            ST_IsValid(geometry) AS valid,
            ST_NumGeometries(geometry) AS n_parts,
            (SELECT coalesce(sum(ST_NumInteriorRings(d.geom)), 0)
               FROM ST_Dump(geometry) AS d) AS n_holes,
            area_km
        FROM map_bounds.map_area
        WHERE id = :source_id
        """,
        dict(source_id=TEST_SOURCE_ID),
    ).one()
    assert area.valid
    assert area.n_parts == 2
    assert area.n_holes == 0
    assert area.area_km > 0
