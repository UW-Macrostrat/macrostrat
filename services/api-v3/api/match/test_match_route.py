from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import mark

from macrostrat.match_utils.test_match_strat_names import cases
from . import router

test_app = FastAPI()
test_app.include_router(router)

client = TestClient(test_app, raise_server_exceptions=True)


def test_match_units_no_params():
    response = client.get("/match/strat-names")
    assert response.status_code == 422  # Missing required parameters
    data = response.json()
    assert "detail" in data


@mark.parametrize("case", cases)
def test_basic_match_units(case):
    response = client.get(
        "/match/strat-names",
        params={
            "lat": case.xy[1],
            "lng": case.xy[0],
            "match_text": case.match_text,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["matches"]
    assert len(matches) >= 1
    best_match = matches[0]

    assert best_match["unit_id"] == case.unit_id
    assert best_match["strat_name_id"] == case.strat_name_id


def test_no_match_units():
    response = client.get(
        "/match/strat-names",
        params={
            "lat": 0.0,
            "lng": 0.0,
            "match_text": "Null Island Basalt",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 0
    assert "messages" in data
    messages = data["messages"]
    assert any("No matches found" in msg["message"] for msg in messages)


def test_multi_match_units():
    response = client.post(
        "/match/strat-names",
        json=[
            {
                "lat": case.xy[1],
                "lng": case.xy[0],
                "match_text": case.match_text,
            }
            for case in cases
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == len(cases)

    for res, case in zip(results, cases):
        matches = res["matches"]
        assert len(matches) >= 1
        best_match = matches[0]

        assert best_match["unit_id"] == case.unit_id
        assert best_match["strat_name_id"] == case.strat_name_id


# Column 1494, lat: 53.11400 | lng: -120.90900 | project 1
# Overlaps Column 2149, project_id 10
# Strat name "Kaza", 5415, unit 41104 (2149), unit 34519 (1494)
# Neoproterozoic


def test_match_units_ambiguous_column():
    response = client.get(
        "/match/strat-names",
        params={
            "lat": 53.11400,
            "lng": -120.90900,
            "match_text": "Kaza",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["matches"]
    assert len(matches) >= 1
    best_match = matches[0]

    # Should match the unit from the higher priority project (1)
    assert best_match["unit_id"] == 34519
    assert best_match["strat_name_id"] == 5415


pos = [-105.6, 40.9]  # Near front range of Colorado
# Jelm Formation. unit id 15503, strat name 981
# Triassic


def test_match_units_time_limited():
    response = client.get(
        "/match/strat-names",
        params={
            "lat": pos[1],
            "lng": pos[0],
            "match_text": "Jelm Formation",
            "max_age": 250.0,
            "min_age": 200.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["matches"]
    assert len(matches) >= 1
    best_match = matches[0]

    assert best_match["unit_id"] == 15503
    assert best_match["strat_name_id"] == 981


def test_match_units_wrong_time_period():
    response = client.get(
        "/match/strat-names",
        params={
            "lat": pos[1],
            "lng": pos[0],
            "match_text": "Jelm Formation",
            "b_age": 200.0,
            "t_age": 100.0,
        },
    )
    # TODO: should "no match" be a 404?
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 0
