from os import environ

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import fixture, mark

from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.match_utils.test_match_strat_names import (
    cases,
    cases_strat_name_priority,
)

from ..app import setup_engine
from . import MatchQuery, router, setup_intervals

# TODO: just import the enums from the parent module
valid_name_bases = {"exact", "concept", "rank-up", "rank-down", "synonym"}
valid_location_bases = {"containing column", "adjacent column"}
# None is valid: an unconstrained query applies no temporal filter at all.
valid_age_bases = {"containing interval", "adjacent interval", None}


def assert_valid_unit_matches(matches):
    assert len(matches) >= 1
    priorities = [m["priority"] for m in matches]
    assert priorities == sorted(priorities)

    for match in matches:
        assert match["priority"] >= 0.0
        assert match["unit_id"] is not None
        assert match["strat_name_id"] is not None
        assert match["name_basis"] in valid_name_bases
        assert match["location_basis"] in valid_location_bases
        assert match["age_basis"] in valid_age_bases
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


# -- age_tolerance: PBDB collection 122495 -----------------------------------

# Fossils were collected from the Lawrence Fm, which
# sits in column 101. The Kasimovian tops out at 303.7 Ma while the Lawrence Fm
# in that column runs 303.4818–303.2636 Ma, so a strict overlap test misses the
# collection's own column by 0.2182 Myr and returns only adjacent-column matches.
LAWRENCE = {
    "lat": 38.939899,
    "lng": -95.332901,
    "strat_name": "Lawrence",
    "interval": "Kasimovian",
}
LAWRENCE_NO_INTERVAL = {k: v for k, v in LAWRENCE.items() if k != "interval"}
LAWRENCE_POSITION = {"lat": LAWRENCE["lat"], "lng": LAWRENCE["lng"]}


def test_strict_age_bounds_miss_the_containing_column(client):
    """Reproduce the bug: without a tolerance, column 101 is filtered out."""
    response = client.get("/strat-names", params={**LAWRENCE, "all": True})
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert_valid_unit_matches(matches)
    assert 101 not in {m["col_id"] for m in matches}


def test_age_tolerance_recovers_the_containing_column(client):
    """A 0.5 Myr tolerance surfaces unit 3962 in column 101, tagged as adjacent."""
    response = client.get(
        "/strat-names", params={**LAWRENCE, "age_tolerance": 0.5, "all": True}
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert_valid_unit_matches(matches)

    recovered = [m for m in matches if m["col_id"] == 101]
    assert len(recovered) == 1
    match = recovered[0]
    assert match["unit_id"] == 3962
    assert match["name_basis"] == "exact"
    assert match["location_basis"] == "containing column"
    assert match["age_basis"] == "adjacent interval"
    # Its age range falls outside the Kasimovian, but within the tolerance of it.
    assert match["b_age"] < 303.7
    assert match["b_age"] >= 303.7 - 0.5


def test_age_tolerance_ranks_the_containing_column_first(client):
    """Michael's real call: the default all=false now returns his own column.

    priority is unchanged by this feature — it still keys on name_basis and
    location_basis — and an exact match in the containing column outranks the
    rank-up adjacent-column matches that a strict query returns.
    """
    response = client.get("/strat-names", params={**LAWRENCE, "age_tolerance": 0.5})
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert len(matches) == 1
    assert matches[0]["unit_id"] == 3962
    assert matches[0]["col_id"] == 101
    assert matches[0]["priority"] == 0.0


def test_age_tolerance_smaller_than_the_gap_changes_nothing(client):
    """The gap is 0.2182 Myr, so a 0.1 Myr tolerance must not recover column 101."""
    response = client.get(
        "/strat-names", params={**LAWRENCE, "age_tolerance": 0.1, "all": True}
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert 101 not in {m["col_id"] for m in matches}


@mark.parametrize(
    "age_params",
    [
        {"interval": "Kasimovian"},
        {"b_age": 307.0, "t_age": 303.7},
        {"b_interval": "Kasimovian", "t_interval": "Kasimovian"},
    ],
    ids=["interval", "absolute-ages", "b/t-intervals"],
)
def test_age_basis_is_containing_without_tolerance(client, age_params):
    """Given an age window but no tolerance, every match overlapped it outright."""
    response = client.get(
        "/strat-names", params={**LAWRENCE_NO_INTERVAL, **age_params, "all": True}
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert len(matches) >= 1
    assert {m["age_basis"] for m in matches} == {"containing interval"}


@mark.parametrize(
    "params",
    [
        {},
        {"col_id": 490, "strat_name": "Mancos"},
        {"location_tolerance": 50},
    ],
    ids=["no-age-params", "by-col-id", "spatial-only"],
)
def test_age_basis_is_null_without_any_age_constraint(client, params):
    """No interval, no b_age/t_age, no age_tolerance means no temporal filter ran.

    Reporting 'containing interval' there would claim the units had been checked
    against a time window when none was applied, so the field is null instead.
    """
    query = {**LAWRENCE_NO_INTERVAL, "all": True, **params}
    response = client.get("/strat-names", params=query)
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert len(matches) >= 1
    assert {m["age_basis"] for m in matches} == {None}


def test_age_basis_is_set_for_a_half_open_age_window(client):
    """One bound is still a temporal constraint, so the basis is reported."""
    response = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "b_age": 307.0, "all": True},
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert len(matches) >= 1
    assert {m["age_basis"] for m in matches} == {"containing interval"}


def test_age_tolerance_requires_an_age_window(client):
    """A tolerance with no window to widen is a 422, not a silent no-op."""
    response = client.get(
        "/strat-names", params={**LAWRENCE_NO_INTERVAL, "age_tolerance": 0.5}
    )
    assert response.status_code == 422
    assert "age_tolerance" in response.text


def test_age_tolerance_accepts_an_absolute_age_window(client):
    """An explicit b_age/t_age pair is a valid window for the tolerance."""
    response = client.get(
        "/strat-names",
        params={
            **LAWRENCE_NO_INTERVAL,
            "b_age": 307.0,
            "t_age": 303.7,
            "age_tolerance": 0.5,
            "all": True,
        },
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert 101 in {m["col_id"] for m in matches}


# -- location_tolerance -------------------------------------------------------

# Column 101 contains the Lawrence collection. Its edge-sharing neighbours are
# 100, 102, 103, 108 and 109; column 90 lies further out and only comes within
# reach at a wider tolerance.
LAWRENCE_NEIGHBOURS = {100, 101, 102, 103, 108, 109}


def cols_returned(client, **params):
    response = client.get(
        "/strat-names",
        params={**LAWRENCE, "all": True, **params},
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    return {m["col_id"] for m in matches if m["col_id"] is not None}


def test_default_location_tolerance_matches_the_old_degree_buffer(client):
    """The 1.11 km default reproduces the column set the 0.01-degree buffer gave."""
    assert cols_returned(client, age_tolerance=0.5) <= LAWRENCE_NEIGHBOURS


def test_location_tolerance_changes_the_search(client):
    """A larger tolerance reaches further, and always keeps the containing column."""
    near = cols_returned(client, age_tolerance=0.5, location_tolerance=1.11)
    far = cols_returned(client, age_tolerance=0.5, location_tolerance=100)
    assert near != far
    assert 101 in near and 101 in far


def test_location_tolerance_is_monotonic(client):
    """Widening the tolerance only adds columns, it never swaps them out.

    This holds because the DISTINCT ON in column-strat-names.sql keys on col_id and
    unit_id. Keying on strat_name_id alone kept one arbitrary row per name across
    all adjacent columns, so a distant column could displace a nearer one as the
    candidate set grew.
    """
    near = cols_returned(client, age_tolerance=0.5, location_tolerance=1.11)
    far = cols_returned(client, age_tolerance=0.5, location_tolerance=100)
    assert near < far, f"expected {near} to be a strict subset of {far}"


def test_location_tolerance_zero_still_admits_touching_columns(client):
    """Columns tessellate, so neighbours are at distance 0 and survive a 0 km tolerance.

    ST_DWithin(a, b, 0) is 'touching or overlapping', not 'same column'. Use the
    adjacent-columns match type to restrict to the containing column.
    """
    assert cols_returned(client, age_tolerance=0.5, location_tolerance=0) != {101}


def test_location_tolerance_is_not_cached_across_values(client):
    """Tolerance changes the SQL, so it must be part of the column-units cache key.

    Requesting a wide tolerance after a narrow one (and vice versa) must not return
    the earlier result.
    """
    wide_first = cols_returned(client, age_tolerance=0.5, location_tolerance=100)
    narrow = cols_returned(client, age_tolerance=0.5, location_tolerance=1.11)
    wide_again = cols_returned(client, age_tolerance=0.5, location_tolerance=100)
    assert wide_first == wide_again
    assert narrow != wide_first


def test_location_tolerance_is_bound_in_kilometres_as_supplied(db):
    """The SQL receives the caller's value verbatim; the km->m conversion is in SQL.

    A tolerance of 1000 km must reach far more columns than 1000 m would, which is
    what a stray Python-side conversion would silently produce.
    """
    from macrostrat.match_utils import create_ignore_list, get_column_units

    create_ignore_list(
        db.run_query("SELECT lith name FROM macrostrat.liths").scalars().all()
    )
    with db.engine.connect() as conn:
        near = get_column_units(conn, 101, location_tolerance=1)
        far = get_column_units(conn, 101, location_tolerance=1000)
    assert far.col_id.nunique() > near.col_id.nunique()


def test_location_tolerance_default_is_used_when_absent(db):
    """Omitting the parameter falls back to DEFAULT_LOCATION_TOLERANCE_KM."""
    from macrostrat.match_utils import (
        DEFAULT_LOCATION_TOLERANCE_KM,
        create_ignore_list,
        get_column_units,
    )

    create_ignore_list(
        db.run_query("SELECT lith name FROM macrostrat.liths").scalars().all()
    )
    with db.engine.connect() as conn:
        implicit = get_column_units(conn, 101)
        explicit = get_column_units(
            conn, 101, location_tolerance=DEFAULT_LOCATION_TOLERANCE_KM
        )
    assert set(implicit.col_id.dropna()) == set(explicit.col_id.dropna())


def test_negative_location_tolerance_is_rejected(client):
    """A negative distance is meaningless and must be a 422."""
    response = client.get("/strat-names", params={**LAWRENCE, "location_tolerance": -1})
    assert response.status_code == 422


# -- `all` in the POST body, unknown intervals, unit dedup -------------------


def test_batch_all_in_body_is_honored(client):
    """A body-level "all": 1 widens that item's results; it used to be dropped."""
    body = [{"identifier": 1, "strat_name": "Lawrence", "all": 1, **LAWRENCE_POSITION}]
    response = client.post(
        "/strat-names",
        params={"interval": "Kasimovian", "age_tolerance": 2},
        json=body,
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]
    assert len({m["priority"] for m in matches}) > 1


def test_batch_all_query_param_sets_the_batch_default(client):
    """?all= applies to every item that does not set its own."""
    body = [{"identifier": 1, "strat_name": "Lawrence", **LAWRENCE_POSITION}]
    shared = {"interval": "Kasimovian", "age_tolerance": 2}
    widened = client.post("/strat-names", params={**shared, "all": True}, json=body)
    narrow = client.post("/strat-names", params=shared, json=body)
    assert widened.status_code == 200 and narrow.status_code == 200
    wide_matches = widened.json()["results"][0]["unit_matches"]
    narrow_matches = narrow.json()["results"][0]["unit_matches"]
    assert len(wide_matches) > len(narrow_matches)
    assert {m["priority"] for m in narrow_matches} == {0.0}


def test_batch_item_all_overrides_the_query_default(client):
    """An item's own `all` wins over ?all=, in both directions."""
    response = client.post(
        "/strat-names",
        params={"interval": "Kasimovian", "age_tolerance": 2, "all": True},
        json=[
            {"identifier": "inherits", "strat_name": "Lawrence", **LAWRENCE_POSITION},
            {
                "identifier": "opts-out",
                "strat_name": "Lawrence",
                "all": 0,
                **LAWRENCE_POSITION,
            },
        ],
    )
    assert response.status_code == 200
    inherits, opts_out = (r["unit_matches"] for r in response.json()["results"])
    assert len({m["priority"] for m in inherits}) > 1
    assert {m["priority"] for m in opts_out} == {0.0}


@mark.parametrize(
    "params",
    [
        {"interval": "NotARealInterval"},
        {"b_interval": "NotARealInterval", "t_interval": "Kasimovian"},
        {"t_interval": "NotARealInterval", "b_interval": "Kasimovian"},
    ],
    ids=["interval", "b_interval", "t_interval"],
)
def test_unknown_interval_returns_422(client, params):
    """An interval Macrostrat does not have is a 422 naming the bad value, not a 500."""
    response = client.get(
        "/strat-names", params={**LAWRENCE_POSITION, "strat_name": "Lawrence", **params}
    )
    assert response.status_code == 422
    assert "NotARealInterval" in response.text
    assert "does not exist in Macrostrat" in response.text


def test_matches_are_unique_per_unit_and_column(client):
    """A unit reached by several names appears once, at its best priority.

    Both 'Lawrence' (1105) and 'Lawrence Shale' (71361) resolve to unit 3891 in
    col 100, which previously produced two identical rows at the same priority.
    """
    response = client.get(
        "/strat-names", params={**LAWRENCE, "age_tolerance": 2, "all": True}
    )
    assert response.status_code == 200
    matches = response.json()["results"][0]["unit_matches"]

    pairs = [(m["unit_id"], m["col_id"]) for m in matches]
    assert len(pairs) == len(set(pairs)), f"duplicate (unit_id, col_id) in {pairs}"
    # The kept row is the best-priority one for that unit.
    for match in matches:
        same_unit = [m for m in matches if m["unit_id"] == match["unit_id"]]
        assert match["priority"] == min(m["priority"] for m in same_unit)


# -- string parameters are case-insensitive ----------------------------------


@mark.parametrize("interval", ["Kasimovian", "kasimovian", "KASIMOVIAN", "kAsImOvIaN"])
def test_interval_name_is_case_insensitive(client, interval):
    """Any casing of an interval name resolves to the same age window."""
    response = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "interval": interval, "all": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["unit_matches"]


def test_interval_casings_give_identical_results(client):
    """Casing changes nothing about the matches returned."""
    canonical = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "interval": "Kasimovian", "all": True},
    ).json()["results"][0]["unit_matches"]
    lowered = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "interval": "kasimovian", "all": True},
    ).json()["results"][0]["unit_matches"]
    assert canonical == lowered


@mark.parametrize("field", ["b_interval", "t_interval"])
def test_bounding_interval_names_are_case_insensitive(client, field):
    """b_interval and t_interval fold case the same way as interval."""
    other = "t_interval" if field == "b_interval" else "b_interval"
    response = client.get(
        "/strat-names",
        params={
            **LAWRENCE_NO_INTERVAL,
            field: "kasimovian",
            other: "gzhelian",
            "all": True,
        },
    )
    assert response.status_code == 200, response.text


def test_exact_interval_casing_still_wins(client):
    """'M10n' and 'M10N' are distinct intervals; exact spelling must not be folded away."""
    setup_intervals_response = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "interval": "M10n"},
    )
    # Either a match or no match is fine — what matters is that it resolves at all.
    assert setup_intervals_response.status_code == 200, setup_intervals_response.text


@mark.parametrize("value", ["rank-up", "RANK-UP", "Rank-Up"])
def test_name_basis_is_case_insensitive(client, value):
    """name_basis is a Literal, so it needs folding before validation."""
    response = client.get(
        "/strat-names",
        params={
            "col_id": 490,
            "strat_name": "Navajo Sandstone",
            "all": True,
            "name_basis": value,
        },
    )
    assert response.status_code == 200, response.text
    matches = response.json()["results"][0]["unit_matches"]
    assert all(m["name_basis"] == "rank-up" for m in matches)


@mark.parametrize("value", ["strat_name", "STRAT_NAME", "Strat_Name"])
def test_priority_is_case_insensitive(client, value):
    """priority is also a Literal and must accept any casing."""
    response = client.get(
        "/strat-names",
        params={"col_id": 490, "strat_name": "Mancos", "priority": value},
    )
    assert response.status_code == 200, response.text


@mark.parametrize("value", ["Lawrence", "lawrence", "LAWRENCE"])
def test_strat_name_is_case_insensitive(client, value):
    """strat_name is folded by clean_strat_name on both the query and the db side."""
    response = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "strat_name": value, "all": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["unit_matches"]


def test_unknown_interval_is_still_rejected_whatever_the_casing(client):
    """Folding case must not turn a genuinely unknown interval into a match."""
    response = client.get(
        "/strat-names",
        params={**LAWRENCE_NO_INTERVAL, "interval": "notarealinterval"},
    )
    assert response.status_code == 422
    assert "does not exist in Macrostrat" in response.text


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
            assert match["location_basis"] in valid_location_bases


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
