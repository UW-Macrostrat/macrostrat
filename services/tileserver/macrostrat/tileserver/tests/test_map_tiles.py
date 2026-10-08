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
    SOURCES_HEADER,
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


class TestSourcesHeader:
    """What a tile says it draws, for the usage-stats pipeline to credit."""

    def test_faces_query_returns_the_sources_with_the_tile(self):
        sql = faces_sql(Detail.slim)
        assert "AS tile" in sql and "AS sources" in sql

    def test_header_is_exposed_to_pages(self, app):
        from starlette.middleware.cors import CORSMiddleware

        cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
        assert SOURCES_HEADER in cors.kwargs["expose_headers"]


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


class TestLegacyCartoRewrite:
    """`/carto-slim` and `/carto` tiles are served from `/map/carto`, under their
    own addresses, once an environment switches `legacy_carto_from_compilation`
    on; before that they are the legacy build."""

    @fixture
    def rewriting(self, app):
        from macrostrat.tileserver import db_settings

        db_settings.legacy_carto_from_compilation = True
        yield
        db_settings.legacy_carto_from_compilation = False

    @fixture
    def served(self, monkeypatch):
        """Stand in for the slug route's renderer, which needs a database,
        and report what it was asked for."""
        from starlette.responses import JSONResponse

        from macrostrat.tileserver import map_tiles

        calls = []

        async def render(request, background_tasks, slug, tile, cache, *args, **kw):
            detail = kw.get("detail", args[1] if len(args) > 1 else None)
            calls.append(slug)
            return JSONResponse(
                {
                    "slug": slug,
                    "tile": [tile.z, tile.x, tile.y],
                    "cache": cache.value,
                    "detail": getattr(detail, "value", str(detail)),
                }
            )

        monkeypatch.setattr(map_tiles, "render_map_tile", render)
        return calls

    def test_slim_is_served_from_the_compilation_build(self, client, rewriting, served):
        res = client.get("/carto-slim/3/1/2")
        assert res.status_code == 200
        assert res.json() == {
            "slug": "carto",
            "tile": [3, 1, 2],
            "cache": "prefer",
            "detail": "slim",
        }

    def test_full_keeps_its_properties_and_query(self, client, rewriting, served):
        res = client.get("/carto/3/1/2?cache=bypass")
        assert res.json()["detail"] == "full"
        assert res.json()["cache"] == "bypass"

    def test_served_under_its_own_address(self, client, rewriting, served):
        # No redirect: the client sees one response at the address it asked for.
        res = client.get("/carto-slim/3/1/2", follow_redirects=False)
        assert res.status_code == 200
        assert str(res.url).endswith("/carto-slim/3/1/2")

    def test_only_tiles_are_rewritten(self, client, rewriting, served):
        # The layer's other routes (its TileJSON) are not tiles.
        client.get("/carto-slim/tilejson.json")
        assert served == []

    def test_off_by_default(self, app):
        from macrostrat.tileserver import db_settings

        assert db_settings.legacy_carto_from_compilation is False


class TestRewriteAddress:
    def test_slim_and_full(self):
        from macrostrat.tileserver import rewrite_legacy_carto

        assert rewrite_legacy_carto("/carto-slim/3/1/2", "") == ("/map/carto/3/1/2", "")
        assert rewrite_legacy_carto("/carto/3/1/2", "cache=bypass") == (
            "/map/carto/3/1/2",
            "cache=bypass&detail=full",
        )
        assert rewrite_legacy_carto("/carto-slim/tilejson.json", "") is None
        assert rewrite_legacy_carto("/map/carto/3/1/2", "") is None
