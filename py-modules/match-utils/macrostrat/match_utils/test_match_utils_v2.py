"""
Tests for the v2 match API response structure and batch endpoint.
"""

from pydantic import BaseModel
from pytest import mark

from . import standardize_names, get_all_matched_units, get_columns_for_location
from .models import MatchResult, MatchType


# -- Batch input test data --------------------------------------------------

test_input = [
    {
        "id": "col:97619",
        "lng": -117.445,
        "lat": 47.650002,
        "max_interval": "Langhian",
        "formation": "Latah",
    },
    {
        "id": "col:106382",
        "lng": -105.283333,
        "lat": 38.916668,
        "max_interval": "Chadronian",
        "formation": "Florissant",
    },
    {"id": "col:113350", "lng": 103.627197, "lat": 50.350101, "max_interval": "Aptian"},
    {
        "id": "col:113371",
        "lng": 119.238609,
        "lat": 41.316387,
        "max_interval": "Callovian",
        "min_interval": "Oxfordian",
        "formation": "Daohugou",
    },
    {
        "id": "col:124194",
        "lng": 19.940001,
        "lat": 54.869999,
        "max_interval": "Priabonian",
    },
    {
        "id": "col:125656",
        "lng": 118.921997,
        "lat": 41.536999,
        "max_interval": "Late Barremian",
        "formation": "Yixian",
        "group": "Jehol",
    },
    {
        "id": "col:128550",
        "lng": 118.714996,
        "lat": 36.549999,
        "max_interval": "Burdigalian",
        "formation": "Shanwang",
    },
    {
        "id": "col:168272",
        "lng": -0.0626,
        "lat": 51.555801,
        "max_interval": "Middle Pleistocene",
        "formation": "Highbury Silts and Sands",
    },
]

# -- Expected response structure --------------------------------------------

expected_response_keys = {"version", "date_accessed", "results", "name_bases"}
expected_result_keys = {"unit_matches", "messages"}
expected_match_keys = {
    "strat_name_id", "strat_name", "strat_rank", "parent_id",
    "concept_id", "concept_name", "unit_id", "col_id", "project_id",
    "depth", "name_basis", "spatial_basis", "t_age", "b_age", "priority",
}
valid_name_bases = {"exact", "concept", "rank-up", "rank-down", "synonym"}
valid_spatial_bases = {"containing column", "adjacent column"}


# -- Unit tests for response structure -------------------------------------

def test_match_result_fields():
    """MatchResult must have all expected fields."""
    for field in expected_match_keys:
        assert field in MatchResult.model_fields


def test_match_result_name_basis_values():
    """name_basis must be one of the known values."""
    from pandas import isna
    result = MatchResult(
        strat_name_id=1,
        strat_name="Test",
        strat_rank="Fm",
        parent_id=None,
        concept_id=None,
        concept_name=None,
        unit_id=1,
        col_id=1,
        project_id=1,
        depth=0,
        name_basis="exact",
        spatial_basis="containing column",
        t_age=100.0,
        b_age=200.0,
        priority=0.0,
    )
    assert result.name_basis in valid_name_bases
    assert result.spatial_basis in valid_spatial_bases


def test_priority_ascending_order(db):
    """Matches returned by assign_priorities must be sorted ascending by priority."""
    names = standardize_names("Navajo")
    with db.engine.connect() as conn:
        rows = get_all_matched_units(conn, 490, names)
    assert len(rows) > 0
    # Priorities from the raw rows (SQL priority column, pre-reassignment)
    priorities = [row["priority"] for row, _ in rows]
    assert priorities == sorted(priorities)


def test_all_false_returns_best_priority_only(client):
    """With all=false (default), only priority=0.0 matches are returned."""
    resp = client.get(
        "/dev/match/strat-names",
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
        "/dev/match/strat-names",
        params={"strat_name": "Navajo Sandstone", "lat": 35.951, "lng": -109.905, "all": True},
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
        "/dev/match/strat-names",
        params={"strat_name": "Navajo Sandstone", "lat": 35.951, "lng": -109.905, "all": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "name_bases" in data
    assert set(data["name_bases"]).issubset(valid_name_bases)


def test_concept_name_excluded_without_concept_param(client):
    """When strat_name is used (not concept_name), concept basis rows are excluded."""
    resp = client.get(
        "/dev/match/strat-names",
        params={"strat_name": "Navajo Sandstone", "lat": 35.951, "lng": -109.905, "all": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    for result in data["results"]:
        for match in result["unit_matches"]:
            assert match["name_basis"] != "concept"


def test_concept_name_included_with_concept_param(client):
    """When concept_name is used, concept basis rows should be present."""
    resp = client.get(
        "/dev/match/strat-names",
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
        "/dev/match/strat-names",
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
    assert any("strat_name" in m["message"] or "concept_name" in m["message"] for m in messages)


def test_unit_matches_sorted_by_priority(client):
    """unit_matches in the response must be in ascending priority order."""
    resp = client.get(
        "/dev/match/strat-names",
        params={"strat_name": "Navajo", "lat": 35.951, "lng": -109.905, "all": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    for result in data["results"]:
        priorities = [m["priority"] for m in result["unit_matches"]]
        assert priorities == sorted(priorities)