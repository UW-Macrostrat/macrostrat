"""Copying a staged map into `maps` (`copy_to_maps`) when it lacks a lines or
points table, or its polygons."""

import pytest

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.insert import copy_to_maps
from macrostrat.map_integration.source_tables import create_source_tables
from macrostrat.map_integration.utils.map_info import get_map_info

MAPS = {999101: "test-polygons-only", 999102: "test-lines-only"}


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        for source_id, slug in MAPS.items():
            _db.run_sql(
                "INSERT INTO maps.sources (source_id, slug, scale) VALUES (:id, :slug, 'large')",
                dict(id=source_id, slug=slug),
                raise_errors=True,
            )
        create_source_tables(_db, "test-polygons-only", kinds=("polygons",))
        create_source_tables(_db, "test-lines-only", kinds=("lines",))
        _db.run_sql(
            """
            INSERT INTO sources.test_polygons_only_polygons
              (source_id, lith, b_interval, t_interval, geom)
            VALUES (999101, 'sandstone', 1, 1,
              ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326)))
            """,
            raise_errors=True,
        )
        _db.session.commit()
        yield _db


def test_missing_lines_and_points_are_skipped(db):
    copy_to_maps(db, get_map_info(db, "test-polygons-only"))
    n = db.run_query(
        "SELECT count(*) FROM maps.polygons WHERE source_id = 999101"
    ).scalar()
    assert n == 1


def test_polygons_are_required(db):
    with pytest.raises(MacrostratError, match="polygons does not exist"):
        copy_to_maps(db, get_map_info(db, "test-lines-only"))
