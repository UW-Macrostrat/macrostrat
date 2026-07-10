from os import environ

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import fixture, mark

from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.match_utils.test_match_strat_names import (
    cases,
    cases_strat_name_priority,
)

from . import MatchQuery, router, setup_intervals
from ..app import setup_engine

# TODO: just import the enums from the parent module
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
    test_app = FastAPI(lifespan=setup_engine)
    test_app.include_router(router)
    # Enter the TestClient as a context manager so Starlette runs the lifespan,
    # which populates app.state.sync_db that the match routes depend on.
    with TestClient(test_app, raise_server_exceptions=True) as client:
        yield client


def test_match_units_no_params(client):
    response = client.get("/strat-names")
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@mark.parametrize("case", cases)
def test_basic_match_units(client, case):
    print(case)
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

    # Default all=false returns exactly one best-priority match. Case returns the concept match not the exact match
    # added another case list to be updated with the new
    assert len(matches) == 1
    best_match = matches[0]
    assert best_match["priority"] == 0.0
    assert best_match["unit_id"] == case.unit_id
    assert best_match["strat_name_id"] == case.strat_name_id


@mark.parametrize("case", cases_strat_name_priority)
def test_basic_match_units_strat_name_priority(client, case):
    response = client.get(
        "/strat-names",
        params={
            "lat": case.xy[1],
            "lng": case.xy[0],
            "strat_name": case.match_text,
            "priority": "strat_name",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    results = data["results"]
    assert len(results) == 1
    matches = results[0]["unit_matches"]
    assert_valid_unit_matches(matches)

    # Default all=false returns exactly one best-priority match. Case returns the concept match not the exact match
    # added another case list to be updated with the new
    assert len(matches) == 1
    best_match = matches[0]
    assert best_match["priority"] == 0.0
    assert best_match["unit_id"] == case.unit_id
    assert best_match["strat_name_id"] == case.strat_name_id


def test_strat_name_and_strat_name_id_returns_error(client):
    """Providing both strat_name and strat_name_id is rejected with a 422."""
    response = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "strat_name_id": 3361,
            "lat": 39.419220,
            "lng": -111.950684,
        },
    )
    assert response.status_code == 422
    body = response.text
    assert "Only one of strat_name or strat_name_id" in body


def test_name_basis_filter(client):
    """name_basis filters results to only matches with that name_basis."""
    # get all possible match bases with all=True so we know which bases are present.
    full = client.get(
        "/strat-names",
        params={"col_id": 490, "strat_name": "Mancos", "all": True},
    )
    assert full.status_code == 200
    full_matches = full.json()["results"][0]["unit_matches"]
    present = {m["name_basis"] for m in full_matches}
    assert present  # sanity: there is something to filter

    # pick one basis to confirm the filter returns only that basis
    target = sorted(present)[0]
    expected = [m for m in full_matches if m["name_basis"] == target]

    filtered = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Mancos",
            "all": True,
            "name_basis": target,
        },
    )
    assert filtered.status_code == 200
    filtered_matches = filtered.json()["results"][0]["unit_matches"]
    assert len(filtered_matches) == len(expected)
    assert all(m["name_basis"] == target for m in filtered_matches)


def test_name_basis_filter_all_false_returns_best_single_match(client):
    """all=false + name_basis returns the best (lowest-priority) match of that basis."""
    # get all possible match bases with all=True so we know which bases are present.
    full = client.get(
        "/strat-names",
        params={"col_id": 490, "strat_name": "Mancos", "all": True},
    )
    assert full.status_code == 200
    full_matches = full.json()["results"][0]["unit_matches"]
    present = {m["name_basis"] for m in full_matches}
    assert present

    target = sorted(present)[0]
    of_basis = [m for m in full_matches if m["name_basis"] == target]
    best_priority = min(m["priority"] for m in of_basis)
    expected_unit_ids = {
        m["unit_id"] for m in of_basis if m["priority"] == best_priority
    }

    resp = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Mancos",
            "all": False,
            "name_basis": target,
        },
    )
    assert resp.status_code == 200
    matches = resp.json()["results"][0]["unit_matches"]
    assert len(matches) >= 1
    # Only the best match of the requested basis are returned.
    assert all(m["name_basis"] == target for m in matches)
    assert all(m["priority"] == best_priority for m in matches)
    assert {m["unit_id"] for m in matches} == expected_unit_ids


def test_name_basis_invalid_value_returns_error(client):
    """An unknown name_basis value is rejected with a 422."""
    response = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Mancos",
            "name_basis": "not-a-basis",
        },
    )
    assert response.status_code == 422


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

    for res, case in zip(results, cases):
        matches = res["unit_matches"]
        assert_valid_unit_matches(matches)

        # Default all=false returns exactly one best-priority match per response.
        assert len(matches) == 1

        best_match = matches[0]
        assert best_match["priority"] == 0.0
        assert best_match["unit_id"] == case.unit_id
        assert best_match["strat_name_id"] == case.strat_name_id


def test_batch_shared_location_via_query_defaults(client):
    """Shared location goes in the query string; the body carries per-item names.

    Each item's `identifier` is echoed back as `id` so callers can correlate,
    and results stay one-per-input in order.
    """
    items = [
        {"identifier": 1000 + i, "strat_name": c.match_text}
        for i, c in enumerate(cases)
    ]
    response = client.post(
        "/strat-names",
        params={"lat": cases[0].xy[1], "lng": cases[0].xy[0]},
        json=items,
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data

    results = data["results"]
    assert len(results) == len(cases)

    for res, case, item in zip(results, cases, items):
        # The supplied identifier is echoed back as `id` for correlation.
        assert res["id"] == item["identifier"]

        matches = res["unit_matches"]
        assert_valid_unit_matches(matches)

        # Default all=false returns exactly one best-priority match per input.
        assert len(matches) == 1
        best_match = matches[0]
        assert best_match["priority"] == 0.0
        assert best_match["unit_id"] == case.unit_id
        assert best_match["strat_name_id"] == case.strat_name_id


def test_batch_col_id_and_all_query_defaults(client):
    """Shared col_id and all=true come from the query string; body items may be partial."""
    response = client.post(
        "/strat-names",
        params={"col_id": 490, "all": True},
        json=[{"identifier": 42, "strat_name": "Mancos"}],
    )
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 1
    assert results[0]["id"] == 42

    matches = results[0]["unit_matches"]
    assert_valid_unit_matches(matches)
    # all=true (shared via query) should return more than the single best match.
    priorities = [m["priority"] for m in matches]
    assert priorities == sorted(priorities)
    assert len(matches) > 1


def test_batch_item_overrides_query_default(client):
    """A field set on a body item overrides the shared query-parameter default."""
    # Shared col_id=490 in the query, but the second item overrides it.
    response = client.post(
        "/strat-names",
        params={"col_id": 490},
        json=[
            {"identifier": "a", "strat_name": "Mancos"},
            {"identifier": "b", "strat_name": "Kaza", "col_id": 495},
        ],
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert [r["id"] for r in results] == ["a", "b"]


def test_batch_missing_location_returns_422(client):
    """An item with no location (and no shared default) is a 422, not a 500."""
    response = client.post(
        "/strat-names",
        json=[{"identifier": 1, "strat_name": "Mancos"}],
    )
    assert response.status_code == 422


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


def test_match_types_all_true(client):
    """With all=true, return all API-supported Mancos matches ordered by priority."""
    response = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Mancos",
            "all": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    print(data)
    results = data["results"]
    print(results)
    assert len(results) == 1

    matches = results[0]["unit_matches"]
    assert_valid_unit_matches(matches)
    print(matches)

    # all=true should return the full ordered match set, not only priority 0.0.
    priorities = [m["priority"] for m in matches]
    assert priorities == sorted(priorities)
    assert len(matches) > 1
    assert len(set(priorities)) > 1

    # This is from an adjacent column and a member within the Mancos shale
    # Graneros Mbr of the Mancos Shale. It should still match.
    # TODO should we match based on unit name? or just named strat names
    assert any(
        m["unit_id"] == 15174
        and m["strat_name"] == "Mancos Shale"
        and m["col_id"] == 495
        for m in matches
    )


def test_match_types_all_false(client):
    """With all=false, return only the best priority-0.0 Mancos match."""
    response = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Mancos",
        },
    )
    assert response.status_code == 200

    data = response.json()
    results = data["results"]
    assert len(results) == 1

    matches = results[0]["unit_matches"]
    assert_valid_unit_matches(matches)

    # Default all=false should return exactly one best match.
    assert len(matches) == 1

    best_match = matches[0]
    assert best_match["priority"] == 0.0
    assert best_match["unit_id"] == 14992
    assert best_match["strat_name"] == "Mancos Shale"


def test_match_brady_butte_pluton(client):
    """Brady Butte Pluton should recover the related Brady Butte igneous unit."""
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
    assert len(matches) == 1
    match = matches[0]
    assert match["unit_id"] == 1852
    assert match["strat_name"] == "Brady Butte Granodiorite"


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


def test_strat_name_query_excludes_concept_basis_for_exact_formation_name(client):
    """an exact formation-name query should not return concept basis matches, only exact matches."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo Sandstone",
            "lat": 39.419220,
            "lng": -111.950684,
            "all": True,
        },
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1

    matches = data["results"][0]["unit_matches"]
    assert_valid_unit_matches(matches)

    name_bases = {match["name_basis"] for match in matches}
    assert name_bases.issubset(valid_name_bases)
    assert "concept" not in name_bases
    assert "concept" not in data["name_bases"]

    # the exact Navajo Sandstone match should be returned
    best_match = matches[0]
    assert best_match["priority"] == 0.0
    assert best_match["unit_id"] == 14623
    assert best_match["strat_name_id"] == 3361
    assert best_match["strat_name"] == "Navajo Sandstone"
    assert best_match["name_basis"] == "exact"


def test_strat_name_query_can_include_concept_basis_for_short_name(client):
    """a concept strat_name query can return the concept name basis match."""
    resp = client.get(
        "/strat-names",
        params={
            "strat_name": "Navajo",
            "lat": 39.419220,
            "lng": -111.950684,
            "all": True,
        },
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 1

    matches = data["results"][0]["unit_matches"]
    assert_valid_unit_matches(matches)

    name_bases = {match["name_basis"] for match in matches}
    assert name_bases.issubset(valid_name_bases)
    assert "concept" in name_bases
    assert "concept" in data["name_bases"]

    # the same Navajo Sandstone unit is returned as a concept match since the strat_name passed
    # does not have any exact matches.
    best_match = matches[0]
    assert best_match["priority"] == 0.0
    assert best_match["unit_id"] == 14623
    assert best_match["strat_name_id"] == 3361
    assert best_match["strat_name"] == "Navajo Sandstone"
    assert best_match["name_basis"] == "concept"


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
