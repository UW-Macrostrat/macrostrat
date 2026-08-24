"""Vector-tile layer wiring.

These run without Docker or a database — they cover the parts that decide
*whether* a tile is cached and *what* gets passed to the SQL function, which is
where a silent regression would hurt most. Whether the cache actually stores
anything is exercised by the integration tests.
"""

from os import environ

from pytest import fixture, mark

from macrostrat.tileserver.vector_tiles import StoredFunction
from macrostrat.tileserver.vector_tiles.factory import (
    queryparams_to_kwargs,
    resolve_cache_mode,
)
from macrostrat.tileserver_utils import CacheMode

# Layers that must keep their database-side tile cache. Losing a profile here
# would silently turn every request into a full re-render, so the mapping is
# pinned rather than merely assumed.
CACHED_LAYERS = {
    "carto": "carto",
    "carto-slim": "carto-slim",
    "carto-slim-rotated": "carto-slim-rotated",
}


@fixture(scope="module")
def app():
    """The real application, imported without touching a database.

    Settings validation needs a URL present; the connection pool is only opened
    by the startup event, which never runs here.
    """
    environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/unused")
    from macrostrat.tileserver import app

    return app


@fixture(scope="module")
def catalog(app):
    return app.state.function_catalog


class TestLayerNames:
    def test_id_strips_schema_and_hyphenates(self):
        assert StoredFunction("tile_layers.carto_slim").id == "carto-slim"
        assert StoredFunction("corelle_macrostrat.igcp_orogens").id == "igcp-orogens"

    def test_function_name_is_preserved(self):
        layer = StoredFunction("tile_layers.carto_slim")
        assert layer.function_name == "tile_layers.carto_slim"


class TestCacheProfiles:
    """The regression guard for database-side caching."""

    @mark.parametrize("layer_id,profile", sorted(CACHED_LAYERS.items()))
    def test_cached_layers_keep_their_profile(self, catalog, layer_id, profile):
        layer = catalog.get(layer_id)
        assert layer is not None, f"{layer_id} is no longer registered"
        assert layer.profile_id == profile

    def test_cached_layers_actually_use_the_cache(self, catalog):
        for layer_id in CACHED_LAYERS:
            layer = catalog.get(layer_id)
            assert resolve_cache_mode(layer, CacheMode.prefer) == CacheMode.prefer

    def test_other_layers_bypass_the_cache(self, catalog):
        uncached = [l for l in catalog.values() if l.id not in CACHED_LAYERS]
        assert uncached, "expected some layers to be served without caching"
        for layer in uncached:
            assert layer.profile_id is None
            assert resolve_cache_mode(layer, CacheMode.prefer) == CacheMode.bypass

    def test_bypass_is_honored_for_cached_layers(self, catalog):
        layer = catalog.get("carto")
        assert resolve_cache_mode(layer, CacheMode.bypass) == CacheMode.bypass


class TestQueryParams:
    def test_scalar_and_repeated_values(self):
        from starlette.datastructures import QueryParams

        params = queryparams_to_kwargs(QueryParams("a=1&b=2&b=3"))
        assert params == {"a": "1", "b": ["2", "3"]}

    def test_cache_is_not_forwarded_to_sql(self):
        """`cache` controls the tile cache; it isn't a layer parameter.

        It also stays out of the cache key, so tiles cached before this
        exclusion existed remain valid.
        """
        from starlette.datastructures import QueryParams

        params = queryparams_to_kwargs(
            QueryParams("cache=bypass&source_id=1409"), ignore_keys=["cache"]
        )
        assert params == {"source_id": "1409"}


class TestRenderedQuery:
    def test_function_is_called_with_xyz_and_json_params(self):
        from morecantile import Tile

        layer = StoredFunction("tile_layers.carto_slim")
        query, params = layer.render_query(Tile(15, 23, 6), source_id="1409")

        assert "tile_layers.carto_slim" in query
        # x, y, z, then the JSON parameter blob.
        assert params[:3] == [15, 23, 6]
        assert params[3] == '{"source_id": "1409"}'


class TestCatchAllScope:
    """The tile route is mounted at the app root, so its reach matters.

    With plain `{z}/{x}/{y}` it matched *any* four-segment path and answered
    "Layer '<first segment>' not found" — which is how it swallowed
    `/rasters/<layer>/point/<lon>,<lat>` and made the raster point query
    unreachable. Typed converters keep it to real tile addresses.
    """

    @fixture(scope="class")
    def routes(self, app):
        from starlette.routing import Match

        def matches(path: str) -> bool:
            scope = {"type": "http", "method": "GET", "path": path, "headers": []}
            for route in app.routes:
                if route.matches(scope)[0] == Match.FULL:
                    return getattr(route, "name", None) == "tile"
            return False

        return matches

    def test_a_tile_address_still_matches(self, routes):
        assert routes("/carto-slim/4/3/5")

    def test_non_numeric_segments_do_not_match(self, routes):
        """Where the bug lived: a raster point query is not a tile address."""
        assert not routes("/rasters/emit-minerals/point/-118.0,36.0")

    def test_a_nested_raster_path_does_not_match(self, routes):
        assert not routes("/rasters/emit-minerals/tiles/WebMercatorQuad")

    def test_tilejson_is_not_claimed_by_the_tile_route(self, routes):
        assert not routes("/carto-slim/tilejson.json")


class TestTileURLTemplate:
    """TileJSON has to hand out `{z}/{x}/{y}`, which typed converters can't build.

    `url_path_for` validates its arguments against the converters, so the
    placeholders have to come from the route's own path instead — and if that
    ever silently produced a concrete address, every TileJSON consumer would
    request the same tile forever.
    """

    @fixture(scope="class")
    def template(self):
        from starlette.requests import Request

        from macrostrat.tileserver.vector_tiles.factory import VectorTileFactory

        factory = VectorTileFactory()
        request = Request(
            {
                "type": "http",
                "headers": [],
                "server": ("testserver", 80),
                "scheme": "http",
                "path": "/",
                "query_string": b"",
            }
        )
        return factory.tile_url_template(request, "tile_layers.carto")

    def test_placeholders_are_literal(self, template):
        assert template.endswith("/{z}/{x}/{y}")

    def test_no_converter_syntax_leaks(self, template):
        """`{z:int}` in a tile URL would break every client that reads it."""
        assert ":int" not in template

    def test_layer_is_substituted(self, template):
        assert "/tile_layers.carto/" in template
