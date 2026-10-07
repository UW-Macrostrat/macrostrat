"""Tests for editing a map's operation list (`bounds.edit`) and `fill_holes`.

Run against ``test_db_base``, which commits, with cleanup by unique ids.
"""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.geometry import create_bounds
from macrostrat.map_integration.utils.map_info import get_map_info
from macrostrat.map_topology.bounds import build, edit

SOURCE_ID = 999002
SLUG = "test_bounds_edit"

# A 10° square with one large hole (~12,000 km²) and one small one (~1 km²).
POLYGON = (
    "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0),"
    " (2 2, 2 3, 3 3, 3 2, 2 2),"
    " (6 6, 6 6.01, 6.01 6.01, 6.01 6, 6 6))"
)

DRAWN = {
    "type": "Polygon",
    "coordinates": [[[20, 0], [20, 1], [21, 1], [21, 0], [20, 0]]],
}


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        _db.run_sql(
            """
            INSERT INTO maps.sources (source_id, slug, name, scale, status_code)
            VALUES (:source_id, :slug, 'Bounds edit test map', 'large', 'active')
            """,
            dict(source_id=SOURCE_ID, slug=SLUG),
        )
        _db.run_sql(
            """
            INSERT INTO maps.polygons (source_id, scale, geom)
            VALUES (:source_id, 'large', ST_GeomFromText(:wkt, 4326))
            """,
            dict(source_id=SOURCE_ID, wkt=POLYGON),
        )
        _db.session.commit()
        assert create_bounds(_db, get_map_info(_db, SLUG))
        yield _db


def _ops(db):
    return [(o.position, o.operation) for o in build.load_ops(db, SOURCE_ID)]


def _holes(db) -> int:
    return db.run_query(
        "SELECT sum(ST_NumInteriorRings((d).geom)) FROM map_bounds.map_area a,"
        " ST_Dump(a.geometry) d WHERE a.source_id = :source_id",
        dict(source_id=SOURCE_ID),
    ).scalar()


def test_fill_holes_keeps_large_holes(db):
    assert _holes(db) == 2
    edit.append(db, SOURCE_ID, edit.validate("fill_holes", {"max_area": "100km2"}))
    db.session.commit()
    result = build.build(db, SOURCE_ID, strict=True)
    assert result.error is None
    assert result.written
    assert _holes(db) == 1


def test_drawn_operation_needs_geometry(db):
    with pytest.raises(edit.EditError):
        edit.append(db, SOURCE_ID, edit.validate("add", {}))
    with pytest.raises(edit.EditError):
        edit.append(
            db, SOURCE_ID, edit.validate("buffer", {"distance": "1km"}), geometry=DRAWN
        )
    with pytest.raises(edit.EditError):
        edit.validate("union", {})


def test_append_move_annotate_remove(db):
    added = edit.append(
        db, SOURCE_ID, edit.validate("add", {}), geometry=DRAWN, note="gap"
    )
    edit.append(db, SOURCE_ID, edit.validate("simplify", {"tolerance": "100m"}))
    db.session.commit()
    assert _ops(db) == [
        (0, "union"),
        (1, "fill_holes"),
        (2, "add"),
        (3, "simplify"),
    ]

    assert edit.move(db, SOURCE_ID, added, 1) == 1
    edit.annotate(db, SOURCE_ID, added, "river gap")
    db.session.commit()
    assert _ops(db)[1] == (1, "add")
    assert build.load_ops(db, SOURCE_ID)[1].note == "river gap"

    removed = edit.remove(db, SOURCE_ID, added)
    db.session.commit()
    assert removed.operation == "add"
    assert _ops(db) == [(0, "union"), (1, "fill_holes"), (2, "simplify")]

    opening = build.load_ops(db, SOURCE_ID)[0].id
    with pytest.raises(edit.EditError):
        edit.remove(db, SOURCE_ID, opening)
    db.session.rollback()


def test_set_geometry(db):
    added = edit.append(db, SOURCE_ID, edit.validate("subtract", {}), geometry=DRAWN)
    db.session.commit()
    moved = {
        "type": "Polygon",
        "coordinates": [[[30, 0], [30, 2], [32, 2], [32, 0], [30, 0]]],
    }
    edit.set_geometry(db, SOURCE_ID, added, moved)
    db.session.commit()
    xmin = db.run_query(
        "SELECT ST_XMin(geometry) FROM map_bounds.boundary_op WHERE id = :id",
        dict(id=added),
    ).scalar()
    assert xmin == 30

    fill = next(o for o in build.load_ops(db, SOURCE_ID) if o.operation == "fill_holes")
    with pytest.raises(edit.EditError):
        edit.set_geometry(db, SOURCE_ID, fill.id, moved)
    db.session.rollback()
