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
    Detail,
    cache_profile,
    faces_sql,
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

    def test_full_detail_is_cached_apart(self):
        # The same tile with more properties: sharing rows would serve either
        # set to both.
        assert cache_profile("carto", Detail.full) == "map-carto-full"
        assert cache_profile("bc-surface", Detail.full) is None

    def test_detail_fills_both_slots(self):
        slim = faces_sql(Detail.slim)
        full = faces_sql(Detail.full)
        for sql in (slim, full):
            assert "::detail" not in sql
        assert "ref_title" in full and "ref_title" not in slim

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


class TestLegacyCartoRedirect:
    """`/carto-slim` and `/carto` tiles go to `/map/carto` once an environment
    switches `redirect_legacy_carto` on; before that they are the legacy build."""

    @fixture
    def redirecting(self, app):
        from macrostrat.tileserver import db_settings

        db_settings.redirect_legacy_carto = True
        yield
        db_settings.redirect_legacy_carto = False

    def test_slim_goes_to_the_compilation_build(self, client, redirecting):
        res = client.get("/carto-slim/3/1/2", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"].endswith("/map/carto/3/1/2")

    def test_full_keeps_its_properties_and_query(self, client, redirecting):
        res = client.get("/carto/3/1/2?cache=bypass", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"].endswith(
            "/map/carto/3/1/2?cache=bypass&detail=full"
        )

    def test_only_tiles_are_redirected(self, client, redirecting):
        # The layer's other routes (its TileJSON) are not tiles.
        res = client.get("/carto-slim/tilejson.json", follow_redirects=False)
        assert res.status_code != 307

    def test_off_by_default(self, client):
        from macrostrat.tileserver import db_settings

        assert db_settings.redirect_legacy_carto is False
