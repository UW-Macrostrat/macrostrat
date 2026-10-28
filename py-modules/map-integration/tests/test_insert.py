"""Copying staged maps into `maps`: one at a time (`copy_to_maps`) when one lacks a
lines or points table or its polygons, and a compilation's members in one pass
(`copy_sources_to_maps`)."""

import pytest

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.process.insert import (
    copy_sources_to_maps,
    copy_to_maps,
    plan_copy,
)
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


#: Members of one compilation sharing `sources.test_comp_*`, at two scales.
MEMBERS = {999201: "large", 999202: "small", 999203: "large"}


@pytest.fixture(scope="module")
def compilation(db):
    for source_id, scale in MEMBERS.items():
        db.run_sql(
            "INSERT INTO maps.sources (source_id, slug, scale)"
            " VALUES (:id, :slug, CAST(:scale AS maps.map_scale))",
            dict(id=source_id, slug=f"test-comp-{source_id}", scale=scale),
            raise_errors=True,
        )
    create_source_tables(db, "test-comp", kinds=("polygons", "lines"))
    for source_id in MEMBERS:
        db.run_sql(
            """
            INSERT INTO sources.test_comp_polygons
              (source_id, lith, b_interval, t_interval, geom)
            VALUES (:id, 'shale', 1, 1, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326)));
            INSERT INTO sources.test_comp_lines (source_id, geom)
            VALUES (:id, ST_Multi(ST_MakeLine(ST_Point(0, 0, 4326), ST_Point(1, 1, 4326))));
            """,
            dict(id=source_id),
            raise_errors=True,
        )
    db.session.commit()
    return db


def maps_rows(db, kind):
    return db.run_query(
        f"SELECT source_id, scale::text AS scale FROM maps.{kind}"
        " WHERE source_id = ANY(:ids) ORDER BY source_id",
        dict(ids=list(MEMBERS)),
    ).all()


def test_a_compilation_copies_in_one_pass_at_each_members_scale(compilation):
    db = compilation
    plan = plan_copy(db, list(MEMBERS), staging_prefix="test_comp")
    # Grouped in `maps.map_scale` order, so the heap appends cluster by scale.
    assert plan.by_scale == {"small": [999202], "large": [999201, 999203]}

    assert copy_sources_to_maps(db, plan) == {"polygons": 3, "lines": 3}
    expected = [(i, s) for i, s in sorted(MEMBERS.items())]
    assert [tuple(r) for r in maps_rows(db, "polygons")] == expected
    assert [tuple(r) for r in maps_rows(db, "lines")] == expected


def test_members_with_features_are_skipped_then_replaced(compilation):
    db = compilation
    plan = plan_copy(db, list(MEMBERS), staging_prefix="test_comp")
    assert plan.targets == [] and sorted(plan.complete) == sorted(MEMBERS)
    assert copy_sources_to_maps(db, plan) == {"polygons": 0, "lines": 0}

    plan = plan_copy(
        db, list(MEMBERS), staging_prefix="test_comp", delete_existing=True
    )
    copy_sources_to_maps(db, plan)
    assert len(maps_rows(db, "polygons")) == 3


def map_ids(db, source_id):
    return db.run_query(
        "SELECT array_agg(map_id ORDER BY map_id) FROM maps.polygons"
        " WHERE source_id = :id",
        dict(id=source_id),
    ).scalar()


def test_an_interrupted_member_is_copied_again_alone(compilation):
    """An old per-member copy that stopped after polygons left its lines out."""
    db = compilation
    db.run_sql("DELETE FROM maps.lines WHERE source_id = 999203", raise_errors=True)
    db.session.commit()
    untouched = map_ids(db, 999201)

    plan = plan_copy(db, list(MEMBERS), staging_prefix="test_comp")
    assert plan.partial == [999203]
    assert plan.targets == [999203]
    assert copy_sources_to_maps(db, plan) == {"polygons": 1, "lines": 1}

    assert len(maps_rows(db, "polygons")) == len(maps_rows(db, "lines")) == 3
    # Complete members are left alone, down to their polygon ids.
    assert map_ids(db, 999201) == untouched
    assert plan_copy(db, list(MEMBERS), staging_prefix="test_comp").targets == []


def test_an_unattributed_member_stops_the_whole_copy(compilation):
    db = compilation
    db.run_sql(
        "UPDATE sources.test_comp_polygons SET lith = NULL WHERE source_id = 999203",
        raise_errors=True,
    )
    db.session.commit()
    before = maps_rows(db, "polygons")
    plan = plan_copy(
        db, list(MEMBERS), staging_prefix="test_comp", delete_existing=True
    )
    assert plan.unattributed == {999203: "lith null on all 1 polygons"}
    with pytest.raises(MacrostratError, match="unattributed"):
        copy_sources_to_maps(db, plan)
    # Refused before the transaction opened: nothing deleted, nothing added.
    assert maps_rows(db, "polygons") == before


def test_a_failure_partway_rolls_back_the_deletes_too(compilation):
    db = compilation
    db.run_sql(
        """
        UPDATE sources.test_comp_polygons SET lith = 'shale' WHERE source_id = 999203;
        INSERT INTO sources.test_comp_polygons (source_id, lith, b_interval, t_interval)
        VALUES (999203, 'shale', 1, 1);
        """,
        raise_errors=True,
    )
    db.session.commit()
    before = maps_rows(db, "polygons")
    plan = plan_copy(
        db, list(MEMBERS), staging_prefix="test_comp", delete_existing=True
    )
    # Deletes, then `small` goes in, then `large` hits the NOT NULL geometry.
    with pytest.raises(Exception, match="null value"):
        copy_sources_to_maps(db, plan)
    assert maps_rows(db, "polygons") == before
    assert len(maps_rows(db, "lines")) == 3
