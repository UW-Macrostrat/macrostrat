"""`maps sources normalize`: geometry type, repair and orig_id on staging tables."""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.commands.normalize_sources import normalize
from macrostrat.map_integration.utils.map_info import get_map_info

MAPS = {
    999201: "test-normalize",
    999202: "test-normalize-ambiguous",
    999203: "test-normalize-legacy",
}

# A bowtie: invalid, and repaired into two parts.
BOWTIE = "POLYGON((0 0, 1 1, 1 0, 0 1, 0 0))"
SQUARE = "POLYGON((2 0, 2 1, 3 1, 3 0, 2 0))"


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        for source_id, slug in MAPS.items():
            _db.run_sql(
                "INSERT INTO maps.sources (source_id, slug, scale)"
                " VALUES (:id, :slug, 'large')",
                dict(id=source_id, slug=slug),
                raise_errors=True,
            )
        # As an old ingest left it: single-part geometry, no orig_id.
        _db.run_sql(
            """
            CREATE TABLE sources.test_normalize_polygons (
              _pkid serial PRIMARY KEY, source_id integer,
              objectid double precision, code integer, area double precision,
              geom geometry(Polygon, 4326)
            );
            INSERT INTO sources.test_normalize_polygons
              (source_id, objectid, code, area, geom)
            VALUES
              (999201, 1, 7, 0.5, ST_GeomFromText(:bowtie, 4326)),
              (999201, 2, 7, 1.5, ST_GeomFromText(:square, 4326));
            CREATE TABLE sources.test_normalize_ambiguous_polygons (
              _pkid serial PRIMARY KEY, source_id integer, orig_id integer,
              a integer, b integer, geom geometry(MultiPolygon, 4326)
            );
            INSERT INTO sources.test_normalize_ambiguous_polygons (source_id, a, b, geom)
            VALUES (999202, 1, 10, ST_Multi(ST_GeomFromText(:square, 4326))),
                   (999202, 2, 20, ST_Multi(ST_GeomFromText(:square, 4326)));
            -- A burwell-era table: gid, early_id/late_id, no source_id, `geometry`
            CREATE TABLE sources.test_normalize_legacy_polygons (
              gid serial PRIMARY KEY, early_id integer, late_id integer,
              geometry geometry(MultiPolygon, 4326)
            );
            INSERT INTO sources.test_normalize_legacy_polygons (early_id, late_id, geometry)
            VALUES (3, 1, ST_Multi(ST_GeomFromText(:square, 4326)));
            """,
            dict(bowtie=BOWTIE, square=SQUARE),
            raise_errors=True,
        )
        _db.session.commit()
        yield _db


def test_dry_run_reports_and_writes_nothing(db):
    (report,) = normalize(db, get_map_info(db, "test-normalize"), apply=False)
    assert report.changes[1:] == [
        "geom polygon → multipolygon",
        "repair 1 invalid geometries",
        "orig_id ← objectid (unique)",
    ]
    assert report.changes[0].startswith("add columns orig_id, omit")
    db.session.rollback()
    kind = db.run_query(
        "SELECT type FROM geometry_columns WHERE f_table_name = 'test_normalize_polygons'"
    ).scalar()
    assert kind == "POLYGON"


def test_normalize(db):
    normalize(db, get_map_info(db, "test-normalize"), apply=True)
    db.session.commit()
    row = db.run_query(
        """
        SELECT bool_and(ST_IsValid(geom)) AS valid,
               array_agg(orig_id ORDER BY orig_id) AS ids,
               (SELECT type FROM geometry_columns
                WHERE f_table_name = 'test_normalize_polygons') AS kind
        FROM sources.test_normalize_polygons
        """
    ).one()
    assert row.valid and row.ids == [1, 2] and row.kind == "MULTIPOLYGON"
    # A second run finds nothing left to change
    (again,) = normalize(db, get_map_info(db, "test-normalize"), apply=True)
    assert again.changes == []


def test_ambiguous_orig_id_is_reported_not_set(db):
    (report,) = normalize(db, get_map_info(db, "test-normalize-ambiguous"), apply=True)
    db.session.commit()
    assert not any(c.startswith("orig_id") for c in report.changes)
    assert "equally plausible" in report.notes[0]
    n = db.run_query(
        "SELECT count(orig_id) FROM sources.test_normalize_ambiguous_polygons"
    ).scalar()
    assert n == 0


def test_legacy_table_is_prepared(db):
    legacy = get_map_info(db, "test-normalize-legacy")
    (planned,) = normalize(db, legacy, apply=False)
    db.session.rollback()
    (report,) = normalize(db, legacy, apply=True)
    db.session.commit()
    assert planned.changes == report.changes
    assert report.changes[:2] == ["rename geometry → geom", "rename gid → _pkid"]
    assert "set source_id on 1 rows" in report.changes
    assert "set intervals from early_id, late_id on 1 rows" in report.changes
    row = db.run_query(
        "SELECT source_id, b_interval, t_interval, orig_id, _pkid"
        " FROM sources.test_normalize_legacy_polygons"
    ).one()
    assert (row.source_id, row.b_interval, row.t_interval) == (999203, 3, 1)
    # gid became the key, so it is not also taken as the identifier
    assert row.orig_id is None
    (again,) = normalize(db, legacy, apply=True)
    assert again.changes == []
