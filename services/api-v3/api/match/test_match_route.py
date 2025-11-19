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
    assert len(results) == 1
    matches = results[0]["matches"]
    assert len(matches) == 0

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
