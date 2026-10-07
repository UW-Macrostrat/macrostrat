"""Opening a polar map's boundary with a polar cap (`bounds.edit.open_cap`).

Run against ``test_db_base``, which commits, with cleanup by unique ids.
"""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.geometry import create_bounds
from macrostrat.map_integration.utils.map_info import get_map_info
from macrostrat.map_topology.bounds import build, edit
from macrostrat.map_topology.bounds.operations import load

SOURCE_ID = 999003
SLUG = "test-bounds-cap"

# Straddles the antimeridian near the pole, as Antarctica's features do.
POLYGON = "MULTIPOLYGON(((170 -80, 170 -70, 180 -70, 180 -80, 170 -80)),((-180 -80, -180 -70, -170 -70, -170 -80, -180 -80)))"

SLIVER = {
    "type": "Polygon",
    "coordinates": [[[0, -62], [0, -60], [10, -60], [10, -62], [0, -62]]],
}


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        _db.run_sql(
            """
            INSERT INTO maps.sources (source_id, slug, name, scale, status_code)
            VALUES (:source_id, :slug, 'Polar cap test map', 'medium', 'active')
            """,
            dict(source_id=SOURCE_ID, slug=SLUG),
            raise_errors=True,
        )
        _db.run_sql(
            """
            INSERT INTO maps.polygons (source_id, scale, geom)
            VALUES (:source_id, 'medium', ST_GeomFromText(:wkt, 4326))
            """,
            dict(source_id=SOURCE_ID, wkt=POLYGON),
            raise_errors=True,
        )
        _db.session.commit()
        assert create_bounds(_db, get_map_info(_db, SLUG))
        yield _db


def test_cap_replaces_the_opening_and_keeps_slivers(db):
    edit.append(db, SOURCE_ID, load("subtract", {}), geometry=SLIVER)
    edit.open_cap(db, SOURCE_ID, -60)
    db.session.commit()

    ops = build.load_ops(db, SOURCE_ID)
    assert [(o.position, o.operation) for o in ops] == [(0, "init"), (1, "subtract")]

    build.build(db, SOURCE_ID, strict=True)
    db.session.commit()
    row = db.run_query(
        """
        SELECT ST_XMin(geometry) AS xmin, ST_XMax(geometry) AS xmax,
               ST_YMin(geometry) AS ymin, ST_YMax(geometry) AS ymax,
               ST_IsValid(geometry) AS valid,
               ST_Covers(geometry, ST_MakeEnvelope(20, -70, 30, -61, 4326)) AS covers,
               ST_Intersects(geometry, ST_MakeEnvelope(2, -61.5, 8, -60.5, 4326)) AS sliver
        FROM map_bounds.map_area WHERE source_id = :source_id
        """,
        dict(source_id=SOURCE_ID),
    ).one()
    assert (row.xmin, row.xmax, row.ymin, row.ymax) == (-180, 180, -90, -60)
    assert row.valid and row.covers
    assert not row.sliver


@pytest.mark.parametrize("edge", [0, -90, 95])
def test_cap_needs_a_latitude(db, edge):
    with pytest.raises(edit.EditError):
        edit.open_cap(db, SOURCE_ID, edge)
