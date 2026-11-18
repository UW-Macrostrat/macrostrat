"""The regions tile route, database-free like `test_map_tiles.py`."""

from os import environ

from pytest import fixture

from macrostrat.tileserver.regions import regions_sql


@fixture(scope="module")
def app():
    environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/unused")
    from macrostrat.tileserver import app

    return app


def test_route_is_not_shadowed_by_the_layer_catalog(app):
    scope = {"type": "http", "method": "GET", "path": "/regions/tiles/3/1/2"}
    for route in app.routes:
        match, _ = route.matches(scope)
        if match.value == 2:  # Match.FULL
            assert route.path == "/regions/tiles/{z}/{x}/{y}"
            return
    raise AssertionError("no route matched")


def test_source_filter_is_only_bound_when_asked_for():
    assert ":source_id" not in regions_sql(by_source=False)
    assert "b.source_id = :source_id" in regions_sql(by_source=True)
    for by_source in (True, False):
        assert ":where" not in regions_sql(by_source=by_source)
