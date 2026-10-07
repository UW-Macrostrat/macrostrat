"""`PATCH /columns/{col_id}/geometry`, against a database templated from the
schema-only test database, with one column to edit."""

from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy import text

from api.app import app
from api.database import AppDatabase, get_database
from api.routes.security import has_access
from macrostrat.database.utils import template_database

COL_ID = 1
SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

SETUP = [
    "INSERT INTO macrostrat.projects (id, slug, project, descrip, timescale_id)"
    " VALUES (1, 'test', 'Test', 'Test', 11)",
    "INSERT INTO macrostrat.col_groups (id, col_group, col_group_long, project_id)"
    " VALUES (1, 'T', 'Test', 1)",
    "INSERT INTO macrostrat.cols (id, col_group_id, project_id, status_code,"
    " col_type, col_position, col, col_name, lat, lng, col_area, created)"
    " VALUES (:col_id, 1, 1, 'active', 'column', '', 1, 'Test', 5, 5, 0, now())",
]


@fixture(scope="module")
def database(test_db_macrostrat_schema_only):
    with template_database(
        test_db_macrostrat_schema_only, close_source_connections=True
    ) as engine:
        database = AppDatabase(engine.url.render_as_string(hide_password=False))
        with database.sync_connection() as conn:
            for statement in SETUP:
                conn.execute(text(statement), {"col_id": COL_ID})
        yield database
        database.sync.engine.dispose()


@fixture(scope="module")
def client(database):
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[has_access] = lambda: True
    # Not entered as a context manager, so the app's own database isn't opened
    yield TestClient(app)
    app.dependency_overrides.clear()


def footprint(database):
    with database.sync_connection() as conn:
        return conn.execute(
            text(
                "SELECT c.lat, c.lng, c.col_area, count(a.id) n_areas"
                " FROM macrostrat.cols c"
                " LEFT JOIN macrostrat.col_areas a ON a.col_id = c.id"
                " WHERE c.id = :col_id GROUP BY c.id"
            ),
            {"col_id": COL_ID},
        ).one()


def test_point_and_region(client, database):
    point = {"type": "Point", "coordinates": [0.75, 0.25]}
    res = client.patch(
        f"/columns/{COL_ID}/geometry", json={"point": point, "region": SQUARE}
    )
    assert res.status_code == 200, res.text
    assert res.json()["notices"] == []

    row = footprint(database)
    assert (float(row.lat), float(row.lng)) == (0.25, 0.75)
    assert row.col_area > 12_000
    assert row.n_areas == 1


def test_region_alone_places_the_point(client, database):
    res = client.patch(f"/columns/{COL_ID}/geometry", json={"region": SQUARE})
    assert res.status_code == 200, res.text
    assert (res.json()["lat"], res.json()["lng"]) == (0.5, 0.5)


def test_point_outside_the_region(client, database):
    point = {"type": "Point", "coordinates": [80, 80]}
    res = client.patch(
        f"/columns/{COL_ID}/geometry", json={"point": point, "region": SQUARE}
    )
    assert res.status_code == 422
    assert "outside" in res.json()["detail"]


def test_line_and_radius_are_reported(client, database):
    body = {
        "point": {"type": "Point", "coordinates": [10, 20]},
        "line": {"type": "LineString", "coordinates": [[10, 20], [11, 21]]},
        "radius_km": 2,
    }
    res = client.patch(f"/columns/{COL_ID}/geometry", json=body)
    assert res.status_code == 200, res.text
    codes = {d["code"] for d in res.json()["notices"]}
    assert codes == {"line-not-stored", "radius-not-stored"}

    row = footprint(database)
    assert (float(row.lat), float(row.lng)) == (20, 10)
    assert row.n_areas == 0, "a point alone clears the region"


def test_missing_column(client):
    point = {"type": "Point", "coordinates": [0, 0]}
    res = client.patch("/columns/999999/geometry", json={"point": point})
    assert res.status_code == 404
