"""Removing a map's exact duplicate features: a staging table loaded twice, and
an `insert` that copied both loads."""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.dedupe import (
    count_duplicates,
    remove_duplicates,
)
from macrostrat.map_integration.process.insert import copy_to_maps
from macrostrat.map_integration.source_tables import create_source_tables
from macrostrat.map_integration.utils.map_info import get_map_info

SOURCE_ID = 999301
SLUG = "test-doubled"

LOAD = """
INSERT INTO sources.test_doubled_polygons (source_id, lith, b_interval, t_interval, geom)
VALUES
  (:id, 'sandstone', 1, 1, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326))),
  (:id, 'shale', 1, 1, ST_Multi(ST_MakeEnvelope(1, 0, 2, 1, 4326))),
  -- Same geometry as the sandstone, different attribute: a distinct feature
  (:id, 'limestone', 1, 1, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326)));
INSERT INTO sources.test_doubled_lines (source_id, geom)
VALUES (:id, ST_Multi(ST_MakeLine(ST_Point(0, 0, 4326), ST_Point(1, 1, 4326))));
"""


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        _db.run_sql(
            "INSERT INTO maps.sources (source_id, slug, scale) VALUES (:id, :slug, 'large')",
            dict(id=SOURCE_ID, slug=SLUG),
            raise_errors=True,
        )
        create_source_tables(_db, SLUG, kinds=("polygons", "lines"))
        # Loaded twice, as a re-run ingest leaves it
        for _ in range(2):
            _db.run_sql(LOAD, dict(id=SOURCE_ID), raise_errors=True)
        _db.session.commit()
        copy_to_maps(_db, get_map_info(_db, SLUG))
        _db.session.commit()
        yield _db


def counts(db):
    return {
        c.table: (c.rows, c.duplicates)
        for c in count_duplicates(db, get_map_info(db, SLUG))
    }


def test_counts_duplicates(db):
    assert counts(db) == {
        "maps.polygons": (6, 3),
        "maps.lines": (2, 1),
        "maps.points": (0, 0),
        "sources.test_doubled_polygons": (6, 3),
        "sources.test_doubled_lines": (2, 1),
    }


def test_removes_duplicates_keeping_the_first(db):
    first = db.run_query(
        "SELECT min(map_id) FROM maps.polygons WHERE source_id = :id",
        dict(id=SOURCE_ID),
    ).scalar()

    deleted = remove_duplicates(db, get_map_info(db, SLUG))

    assert deleted["maps.polygons"] == 3
    assert deleted["sources.test_doubled_polygons"] == 3
    assert all(dupes == 0 for _, dupes in counts(db).values())
    liths = db.run_query(
        "SELECT lith FROM maps.polygons WHERE source_id = :id ORDER BY lith",
        dict(id=SOURCE_ID),
    ).scalars()
    assert list(liths) == ["limestone", "sandstone", "shale"]
    kept = db.run_query(
        "SELECT min(map_id) FROM maps.polygons WHERE source_id = :id",
        dict(id=SOURCE_ID),
    ).scalar()
    assert kept == first
