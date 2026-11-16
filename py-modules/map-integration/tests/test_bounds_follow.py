"""Tests for the `follow` opening: one source's boundary copied from another's.

Run against ``test_db_base``, which commits, with cleanup by unique ids.
"""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.geometry import create_bounds
from macrostrat.map_integration.utils.map_info import get_map_info
from macrostrat.map_topology.bounds import build, edit

LEADER = (999011, "test-follow-leader", "POLYGON((0 0, 0 4, 4 4, 4 0, 0 0))")
FOLLOWER = (999012, "test-follow-follower", "POLYGON((1 1, 1 2, 2 2, 2 1, 1 1))")


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        for source_id, slug, wkt in (LEADER, FOLLOWER):
            _db.run_sql(
                """
                INSERT INTO maps.sources (source_id, slug, name, scale, status_code)
                VALUES (:source_id, :slug, :name, 'large', 'active')
                """,
                dict(source_id=source_id, slug=slug, name=slug),
                raise_errors=True,
            )
            _db.run_sql(
                """
                INSERT INTO maps.polygons (source_id, scale, geom)
                VALUES (:source_id, 'large', ST_GeomFromText(:wkt, 4326))
                """,
                dict(source_id=source_id, wkt=wkt),
                raise_errors=True,
            )
            _db.session.commit()
            assert create_bounds(_db, get_map_info(_db, slug))
        yield _db


def _same_bounds(db) -> bool:
    return db.run_query(
        """
        SELECT ST_Equals(l.geometry, f.geometry)
        FROM map_bounds.map_area l, map_bounds.map_area f
        WHERE l.source_id = :leader AND f.source_id = :follower
        """,
        dict(leader=LEADER[0], follower=FOLLOWER[0]),
    ).scalar()


def test_follow_needs_a_source(db):
    with pytest.raises(ValueError):
        build.set_opening(db, FOLLOWER[0], "follow")
    db.session.rollback()


def test_follow_copies_the_boundary(db):
    build.set_opening(db, FOLLOWER[0], "follow", dict(source=LEADER[1]))
    db.session.commit()
    assert not _same_bounds(db)

    dry = build.build(db, FOLLOWER[0], dry_run=True)
    assert dry.error is None and not dry.unchanged
    assert not _same_bounds(db)

    result = build.build(db, FOLLOWER[0])
    assert result.error is None and result.written
    assert _same_bounds(db)
    assert FOLLOWER[0] not in build.needs_build(db)


def test_follower_is_stale_when_the_leader_moves(db):
    edit.append(db, LEADER[0], edit.validate("buffer", {"distance": "50km"}))
    edit.append(db, LEADER[0], edit.validate("simplify", {"tolerance": "20km"}))
    db.session.commit()
    assert build.build(db, LEADER[0], strict=True).written
    assert FOLLOWER[0] in build.needs_build(db)

    order = [m.map_id for m in build.stale_sources(db, rebuild=True)]
    assert order.index(FOLLOWER[0]) > order.index(LEADER[0])

    assert build.build(db, FOLLOWER[0], strict=True).written
    assert _same_bounds(db)
    assert FOLLOWER[0] not in build.needs_build(db)
