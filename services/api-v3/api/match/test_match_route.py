from os import environ

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import fixture, mark

from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.match_utils.test_match_strat_names import cases

from . import MatchQuery, router, setup_intervals

valid_name_bases = {"exact", "concept", "rank-up", "rank-down", "synonym"}
valid_spatial_bases = {"containing column", "adjacent column"}


def assert_valid_unit_matches(matches):
    assert len(matches) >= 1
    priorities = [m["priority"] for m in matches]
    assert priorities == sorted(priorities)

    for match in matches:
        assert match["priority"] >= 0.0
        assert match["unit_id"] is not None
        assert match["strat_name_id"] is not None
        assert match["name_basis"] in valid_name_bases
        assert match["spatial_basis"] in valid_spatial_bases
        assert "concept_name" in match


@fixture(scope="module")
def client(env_db):
    environ["MACROSTRAT_DATABASE_URL"] = raw_database_url(env_db.engine.url)
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app, raise_server_exceptions=True)


def test_match_units_no_params(client):
    response = client.get("/strat-names")
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@mark.parametrize("case", cases)
def test_basic_match_units(client, case):
    response = client.get(
        "/strat-names",
        params={
            "lat": case.xy[1],
            "lng": case.xy[0],
            "strat_name": case.match_text,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["unit_matches"]
    assert_valid_unit_matches(matches)

    # Default all=false returns only the highest-priority API matches.
    assert {m["priority"] for m in matches} == {0.0}


def test_no_match_units(client):
    response = client.get(
        "/strat-names",
        params={
            "lat": 0.0,
            "lng": 0.0,
            "strat_name": "Null Island Basalt",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    assert len(results[0]["unit_matches"]) == 0


def test_multi_match_units(client):
    response = client.post(
        "/strat-names",
        json=[
            {
                "lat": c.xy[1],
                "lng": c.xy[0],
                "strat_name": c.match_text,
            }
            for c in cases
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == len(cases)

    for res in results:
        matches = res["unit_matches"]
        assert_valid_unit_matches(matches)
        assert {m["priority"] for m in matches} == {0.0}


def test_match_units_ambiguous_column(client):
    response = client.get(
        "/strat-names",
        params={
            "lat": 53.11400,
            "lng": -120.90900,
            "strat_name": "Kaza",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["unit_matches"]
    assert len(matches) >= 1
    best_match = matches[0]
    assert best_match["priority"] == 0.0
    assert best_match["unit_id"] == 34519
    assert best_match["strat_name_id"] == 5415


pos = [-105.6, 40.9]


def test_match_units_time_limited(client):
    response = client.get(
        "/strat-names",
        params={
            "lat": pos[1],
            "lng": pos[0],
            "strat_name": "Jelm Formation",
            "b_age": 250.0,
            "t_age": 200.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["unit_matches"]
    assert len(matches) >= 1
    best_match = matches[0]
    assert best_match["unit_id"] == 15503
    assert best_match["strat_name_id"] == 981


def test_match_units_wrong_time_period(client):
    response = client.get(
        "/strat-names",
        params={
            "lat": pos[1],
            "lng": pos[0],
            "strat_name": "Jelm Formation",
            "b_age": 200.0,
            "t_age": 100.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    assert len(results[0]["unit_matches"]) == 0


def test_age_constraints(db):
    setup_intervals(db)
    data = MatchQuery(
        lat=40.9,
        lng=-105.6,
        strat_name="Jelm Formation",
        b_age=250.0,
        t_age=200.0,
    )
    age_range = data.get_age_range()
    assert age_range.b_age == 250.0
    assert age_range.t_age == 200.0


def test_age_constraints_interval(client):
    response = client.get(
        "/strat-names",
        params={
            "lat": pos[1],
            "lng": pos[0],
            "strat_name": "Jelm Formation",
            "interval": "Triassic",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["unit_matches"]
    assert len(matches) >= 1
    best_match = matches[0]
    assert best_match["unit_id"] == 15503
    assert best_match["strat_name_id"] == 981
    assert best_match["t_age"] >= 200.0
    assert best_match["b_age"] <= 260.0


def test_invalid_age_constraints(client):
    response = client.get(
        "/strat-names",
        params={
            "lat": 40.0,
            "lng": -105.0,
            "strat_name": "Some Formation",
            "b_interval": "Oligocene",
            "t_age": 200.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    messages = results[0]["messages"]
    assert any("Inconsistent age constraints" in msg["message"] for msg in messages)


def test_match_types(client):
    """With all=true, return API-supported Brady Butte matches ordered by priority."""
    response = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Brady Butte Pluton",
            "all": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["unit_matches"]
    assert_valid_unit_matches(matches)

    assert any(
        m["unit_id"] == 1852 and m["strat_name"] == "Brady Butte Granodiorite"
        for m in matches
    )


def test_all_false_returns_best_priority_only(client):
    """With all=false (default), only priority=0.0 matches are returned."""
    resp = client.get(
        "/strat-names",
        params={"strat_name": "Navajo Sandstone", "lat": 35.951, "lng": -109.905},
    )
    assert resp.status_code == 200
    data = resp.json()
    for result in data["results"]:
        for match in result["unit_matches"]:
            assert match["priority"] == 0.0


def test_all_true_returns_multiple_matches(client):
    """With all=true, multiple priority levels should be present."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "lat": 35.951,
            "lng": -109.905,
            "all": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    all_priorities = [
        match["priority"]
        for result in data["results"]
        for match in result["unit_matches"]
    ]
    assert len(set(all_priorities)) > 1


def test_response_has_name_bases(client):
    """Response must include name_bases set."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "lat": 35.951,
            "lng": -109.905,
            "all": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "name_bases" in data
    assert set(data["name_bases"]).issubset(valid_name_bases)


def test_strat_name_query_can_include_computed_concept_basis(client):
    """A strat_name query may include computed concept-basis matches with all=true."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "lat": 35.951,
            "lng": -109.905,
            "all": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    all_bases = [
        match["name_basis"]
        for result in data["results"]
        for match in result["unit_matches"]
    ]
    assert set(all_bases).issubset(valid_name_bases)
    assert "concept" in all_bases


def test_concept_name_included_with_concept_param(client):
    """When concept_name is used, concept basis rows should be present."""
    resp = client.get(
        "/strat-names",
        params={"concept_name": "Navajo", "lat": 35.951, "lng": -109.905, "all": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    all_bases = [
        match["name_basis"]
        for result in data["results"]
        for match in result["unit_matches"]
    ]
    assert "concept" in all_bases


def test_strat_name_and_concept_name_returns_error(client):
    """Providing both strat_name and concept_name should return an error."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "concept_name": "Navajo",
            "lat": 35.951,
            "lng": -109.905,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    messages = data["results"][0]["messages"]
    assert any(
        "strat_name" in m["message"] or "concept_name" in m["message"] for m in messages
    )


def test_unit_matches_sorted_by_priority(client):
    """unit_matches in the response must be in ascending priority order."""
    resp = client.get(
        "/strat-names",
        params={"strat_name": "Navajo", "lat": 35.951, "lng": -109.905, "all": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    for result in data["results"]:
        priorities = [m["priority"] for m in result["unit_matches"]]
        assert priorities == sorted(priorities)


def test_name_basis_values_are_valid(client):
    """All name_basis values in the response must be from the known set."""
    resp = client.get(
        "/strat-names",
        params={"strat_name": "Navajo", "lat": 35.951, "lng": -109.905, "all": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    for result in data["results"]:
        for match in result["unit_matches"]:
            assert match["name_basis"] in valid_name_bases
            assert match["spatial_basis"] in valid_spatial_bases


def test_match_result_has_concept_name(client):
    """Each match result should include concept_name field."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "lat": 35.951,
            "lng": -109.905,
            "all": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    for result in data["results"]:
        for match in result["unit_matches"]:
            assert "concept_name" in match
