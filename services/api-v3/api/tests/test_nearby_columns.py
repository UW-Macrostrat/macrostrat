"""`GET /columns/{col_id}/nearby`, against a database templated from the
schema-only test database, with one region and the columns around it."""

from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy import text

from api.app import app
from api.database import AppDatabase, get_database
from macrostrat.database.utils import template_database

SUBJECT = 1


def square(x0, y0, x1, y1):
    return f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"


#: (id, project, status, point, region)
COLUMNS = [
    (SUBJECT, 1, "active", "POINT(0.5 0.5)", square(0, 0, 1, 1)),
    (2, 1, "active", "POINT(0.25 0.25)", None),
    (3, 2, "in process", "POINT(0.75 0.5)", None),
    (4, 2, "active", "POINT(1.5 0.5)", square(0.5, 0, 1.5, 1)),
    (5, 2, "active", "POINT(1.5 0.2)", square(1, 0, 2, 1)),
    (6, 3, "active", "POINT(1.1 0.5)", None),
    (7, 3, "obsolete", "POINT(0.6 0.6)", None),
    (8, 3, "active", "POINT(5 5)", None),
    # Another hole at the same site, ~330 m off
    (9, 3, "active", "POINT(5.003 5)", None),
]


@fixture(scope="module")
def database(test_db_macrostrat_schema_only):
    with template_database(
        test_db_macrostrat_schema_only, close_source_connections=True
    ) as engine:
        database = AppDatabase(engine.url.render_as_string(hide_password=False))
        with database.sync_connection() as conn:
            for project in (1, 2, 3):
                conn.execute(
                    text(
                        "INSERT INTO macrostrat.projects"
                        " (id, slug, project, descrip, timescale_id)"
                        " VALUES (:p, 'p' || :p, 'Project ' || :p, '', 11)"
                    ),
                    {"p": project},
                )
                conn.execute(
                    text(
                        "INSERT INTO macrostrat.col_groups"
                        " (id, col_group, col_group_long, project_id)"
                        " VALUES (:p, 'G', 'Group', :p)"
                    ),
                    {"p": project},
                )
            for col_id, project, status, point, region in COLUMNS:
                conn.execute(
                    text(
                        "INSERT INTO macrostrat.cols (id, col_group_id, project_id,"
                        " status_code, col_type, col_position, col, col_name, lat, lng,"
                        " col_area, created, coordinate, poly_geom)"
                        " SELECT :id, :p, :p, CAST(:status AS macrostrat.cols_status_code),"
                        # Regions stand for composites, points for measured sections
                        " CASE WHEN CAST(:region AS text) IS NULL THEN 'section'"
                        " ELSE 'column' END::macrostrat.cols_col_type, '', :id,"
                        " 'Column ' || :id, ST_Y(pt), ST_X(pt), 0,"
                        " now(), pt, ST_GeomFromText(:region, 4326)"
                        " FROM ST_GeomFromText(:point, 4326) pt"
                    ),
                    dict(
                        id=col_id, p=project, status=status, point=point, region=region
                    ),
                )
        yield database
        database.sync.engine.dispose()


@fixture(scope="module")
def client(database):
    app.dependency_overrides[get_database] = lambda: database
    yield TestClient(app)
    app.dependency_overrides.clear()


def relations(result):
    return {
        c["col_id"]: c["relation"] for p in result["projects"] for c in p["columns"]
    }


def test_overlapping_and_adjacent(client):
    res = client.get(f"/columns/{SUBJECT}/nearby")
    assert res.status_code == 200, res.text
    # Points inside and an overlapping region overlap, the own project's
    # included; an edge-sharing region is nearby. A point ~11 km off is
    # beyond the default kilometre; obsolete and far columns are left out.
    assert relations(res.json()) == {
        2: "overlaps",
        3: "overlaps",
        4: "overlaps",
        5: "nearby",
    }


def test_holes_at_one_site(client):
    result = client.get("/columns/8/nearby").json()
    assert relations(result) == {9: "nearby"}
    (column,) = result["projects"][0]["columns"]
    assert 0.3 < column["distance_km"] < 0.4
    assert (result["col_type"], column["col_type"]) == ("section", "section")


def test_column_types(client):
    result = client.get(f"/columns/{SUBJECT}/nearby").json()
    types = {
        c["col_id"]: c["col_type"] for p in result["projects"] for c in p["columns"]
    }
    assert result["col_type"] == "column"
    assert types == {2: "section", 3: "section", 4: "column", 5: "column"}


def test_wider_radius(client):
    result = client.get(f"/columns/{SUBJECT}/nearby", params={"radius_km": 25})
    assert relations(result.json())[6] == "nearby"


def test_own_project_then_most_overlapping(client):
    projects = client.get(
        f"/columns/{SUBJECT}/nearby", params={"radius_km": 25}
    ).json()["projects"]
    # Project 2 overlaps most, but the subject's own project leads
    assert [p["project_id"] for p in projects] == [1, 2, 3]
    assert (projects[1]["n_columns"], projects[1]["n_overlapping"]) == (3, 2)


def test_overlap_fraction_for_regions_only(client):
    result = client.get(f"/columns/{SUBJECT}/nearby").json()
    columns = {c["col_id"]: c for p in result["projects"] for c in p["columns"]}
    assert 0.45 < columns[4]["overlap_fraction"] < 0.55
    assert columns[3]["overlap_fraction"] is None


def test_point_finds_the_region_around_it(client):
    result = client.get("/columns/3/nearby", params={"radius_km": 0}).json()
    assert relations(result) == {SUBJECT: "overlaps", 4: "overlaps"}


def test_per_project_cap(client):
    result = client.get(
        f"/columns/{SUBJECT}/nearby", params={"per_project": 1, "radius_km": 25}
    ).json()
    by_project = {p["project_id"]: p for p in result["projects"]}
    assert set(by_project) == {1, 2, 3}
    assert [len(p["columns"]) for p in by_project.values()] == [1, 1, 1]
    assert by_project[2]["n_columns"] == 3


def test_other_projects_only(client):
    result = client.get(
        f"/columns/{SUBJECT}/nearby", params={"include_same_project": False}
    ).json()
    assert [p["project_id"] for p in result["projects"]] == [2]


def test_missing_column(client):
    assert client.get("/columns/999/nearby").status_code == 404
