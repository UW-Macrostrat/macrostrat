"""The slug tile route: who may ask for what, and where it is cached.

Database-free, like `test_auth.py`: the decisions this route makes before it
touches the database -- which slugs are public, which get the cache, that a
guarded slug is refused without a token -- are the ones worth pinning. Rendering
is covered by the integration tests once the dump carries the compilation schema.
"""

from os import environ

from fastapi.testclient import TestClient
from pytest import fixture

from macrostrat.tileserver.map_tiles import (
    CACHE_PROFILES,
    LEGACY_CARTO,
    PUBLIC_SLUGS,
    SCOPE,
    cache_profile,
    is_public,
)


@fixture(scope="module")
def app():
    environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/unused")
    from macrostrat.tileserver import app

    return app


@fixture(scope="module")
def client(app):
    return TestClient(app)


def routes(app):
    return {r.path for r in app.routes if hasattr(r, "path")}


class TestPolicy:
    def test_only_carto_and_its_legacy_alias_are_public(self):
        assert PUBLIC_SLUGS == {"carto", LEGACY_CARTO}
        assert is_public("carto")
        assert is_public("sys:carto-legacy")
        assert not is_public("bc-surface")
        assert not is_public("3400")

    def test_only_carto_and_its_legacy_alias_are_cached(self):
        assert cache_profile("carto") == "map-carto"
        # The alias renders `carto-slim` unparameterized, so it shares its rows.
        assert cache_profile(LEGACY_CARTO) == "carto-slim"
        assert cache_profile("bc-surface") is None
        assert set(CACHE_PROFILES) == PUBLIC_SLUGS

    def test_scope_is_a_valid_delegated_token_scope(self):
        import re

        assert re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*$", SCOPE)


class TestRouting:
    def test_slug_route_and_alias_are_mounted(self, app):
        paths = routes(app)
        assert "/map/{slug}/{z:int}/{x:int}/{y:int}" in paths
        assert "/dev/carto/{z:int}/{x:int}/{y:int}" in paths
        # The catalog's numeric route stays as the v2 alias.
        assert "/{layer}/{z:int}/{x:int}/{y:int}" in paths

    def test_guarded_slug_is_refused_before_any_database_work(self, client):
        # No pool is attached to the app in this test, so a request that reached
        # the database would error rather than 401.
        res = client.get("/map/bc-surface/1/0/0")
        assert res.status_code == 401
        assert res.headers["WWW-Authenticate"] == "Bearer"

    def test_numeric_id_is_a_slug_too_and_therefore_guarded(self, client):
        assert client.get("/map/3400/1/0/0").status_code == 401

    def test_nontile_tail_is_not_a_tile(self, client):
        assert client.get("/map/carto/1/0/notatile").status_code == 404
