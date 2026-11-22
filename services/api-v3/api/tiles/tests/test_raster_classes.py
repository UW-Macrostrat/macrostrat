"""Macrostrat's `?classes=` shorthand on categorical raster layers.

The filtering itself belongs to `macrostrat.raster_layers` and is tested there.
What's Macrostrat-specific — and so tested here — is the flat query parameter
this tile server layers on top of it, and the fact that adding it doesn't cost
the generic `?algorithm=` form.
"""

import pytest

from api.tiles.rasters import (
    NAMED_LAYER_PREFIX,
    _class_filter_dependency,
    _named_layer_router,
)

pytest.importorskip("macrostrat.raster_layers")

from macrostrat.raster_layers import ClassFilter  # noqa: E402


@pytest.fixture(scope="module")
def shorthand():
    return _class_filter_dependency()


class TestShorthand:
    def test_names_become_a_class_filter(self, shorthand):
        result = shorthand(classes="Alunite,Muscovite", algorithm=None)
        assert isinstance(result, ClassFilter)
        assert result.classes == ["Alunite", "Muscovite"]

    def test_whitespace_is_trimmed(self, shorthand):
        """So a hand-written URL can be readable."""
        result = shorthand(classes=" Muscovite , Alunite ", algorithm=None)
        assert result.classes == ["Muscovite", "Alunite"]

    def test_a_single_name_works(self, shorthand):
        assert shorthand(classes="Alunite", algorithm=None).classes == ["Alunite"]

    def test_absent_means_no_post_processing(self, shorthand):
        assert shorthand(classes=None, algorithm=None) is None

    def test_empty_means_no_post_processing(self, shorthand):
        """`?classes=` with nothing after it shows the whole layer."""
        assert shorthand(classes="", algorithm=None) is None
        assert shorthand(classes=" , ", algorithm=None) is None

    def test_explicit_algorithm_wins(self, shorthand):
        """The generic form is the more specific request, so it takes precedence."""
        explicit = ClassFilter(classes=["Kaolin"])
        assert shorthand(classes="Alunite", algorithm=explicit) is explicit

    def test_generic_form_still_passes_through(self, shorthand):
        explicit = ClassFilter(classes=["Kaolin"])
        assert shorthand(classes=None, algorithm=explicit) is explicit


class TestRoutes:
    """The parameter has to be visible in the spec, not just work.

    The OpenAPI spec is how the tile API's contract is read (and reconciled
    against clients), so a shorthand that worked but wasn't described would be
    worse than no shorthand.
    """

    @pytest.fixture(scope="class")
    def tile_params(self):
        """Query parameters on the tile route, as the published spec reports them.

        Read from the OpenAPI document rather than the route's own dependant,
        because parameters contributed by sub-dependencies (which is what both
        `?classes=` and titiler's `?algorithm=` are) only appear once FastAPI has
        flattened them — the same flattening a client sees.
        """
        from fastapi import FastAPI

        from macrostrat.raster_index import RasterIndex

        # A lazy engine: building routes never touches the database.
        index = RasterIndex("postgresql://unused:unused@localhost:1/unused")

        app = FastAPI()
        prefix = NAMED_LAYER_PREFIX
        app.include_router(_named_layer_router(index, prefix), prefix=prefix)
        paths = app.openapi()["paths"]
        path = f"{prefix}/tiles/{{tileMatrixSetId}}/{{z}}/{{x}}/{{y}}@{{scale}}x.{{format}}"
        return {p["name"] for p in paths[path]["get"]["parameters"]}

    def test_classes_is_documented(self, tile_params):
        assert "classes" in tile_params

    def test_generic_algorithm_params_survive(self, tile_params):
        """Replacing the post-process dependency must not drop titiler's own."""
        assert {"algorithm", "algorithm_params"} <= tile_params

    def test_layer_resampling_default_is_preserved(self, tile_params):
        """Categorical rasters must stay `nearest`, and stay overridable."""
        assert "resampling" in tile_params


class TestTileMatrixSets:
    """These layers serve one grid, and it isn't a style choice.

    Asset selection computes tile extents with `ST_TileEnvelope`, which is Web
    Mercator by definition — a request in another grid would select assets for
    the wrong ground. titiler advertises every grid morecantile knows by
    default, so restricting this closes a real hole.
    """

    def test_only_web_mercator(self):
        from api.tiles.rasters import _supported_tms

        assert _supported_tms().list() == ["WebMercatorQuad"]

    def test_other_grids_are_rejected(self, app):
        from fastapi.testclient import TestClient

        client = TestClient(app)
        path = "/rasters/layer/emit-minerals/tiles/{tms}/8/44/100@2x.png"
        response = client.get(path.format(tms="EuropeanETRS89_LAEAQuad"))
        assert response.status_code == 422


class TestWMTS:
    """A WMTS layer per class, so a GIS client gets a picklist of minerals.

    No OGC standard filters a raster by pixel value; advertising each class as
    its own layer is the standardized equivalent, and it is the difference
    between picking "Alunite" in QGIS's dialog and hand-editing a query string.
    """

    class FakeCategory:
        def __init__(self, label):
            self.label = label

    class FakeBackend:
        input = ["emit-minerals"]

    class FakeIndex:
        def __init__(self, categories):
            self._categories = categories
            self.asked = []

        def get_categories(self, layer):
            self.asked.append(layer)
            return self._categories

    def test_one_render_per_class(self):
        from api.tiles.rasters import _class_renders

        index = self.FakeIndex(
            [self.FakeCategory("Alunite"), self.FakeCategory("Kaolin")]
        )
        renders = _class_renders(index)(self.FakeBackend)
        assert renders == {
            "Alunite": {"classes": "Alunite"},
            "Kaolin": {"classes": "Kaolin"},
        }

    def test_no_vocabulary_means_no_extra_layers(self):
        """A layer without class names still gets WMTS, just the one layer."""
        from api.tiles.rasters import _class_renders

        assert _class_renders(self.FakeIndex([]))(self.FakeBackend) == {}

    def test_vocabulary_is_read_per_request(self):
        """So classes added later appear without restarting the tile server."""
        from api.tiles.rasters import _class_renders

        index = self.FakeIndex([self.FakeCategory("Alunite")])
        get_renders = _class_renders(index)
        get_renders(self.FakeBackend)
        get_renders(self.FakeBackend)
        assert index.asked == ["emit-minerals", "emit-minerals"]

    def test_capabilities_route_is_registered(self, app):
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/rasters/layer/{layer}/WMTSCapabilities.xml" in paths


class TestAdvertisedURLsResolve:
    """Every URL a layer hands out must actually be fetchable.

    Mounting a router does not tell it where it lives, and titiler builds
    absolute URLs from `router_prefix`. Leaving that empty made TileJSON and the
    WMTS `ResourceURL` templates advertise `/tiles/...` rather than
    `/rasters/layer/<slug>/tiles/...` — so every one of them 404'd, and QGIS found
    nothing. Macrostrat's own web client never noticed because it builds tile
    URLs itself, which is precisely why this needs a test.
    """

    @staticmethod
    def _concrete(url: str) -> str:
        """A fetchable path from a tile template."""
        path = url.split("testserver", 1)[-1]
        for placeholder, value in [
            ("{z}", "8"),
            ("{x}", "44"),
            ("{y}", "100"),
            ("{TileMatrix}", "8"),
            ("{TileCol}", "44"),
            ("{TileRow}", "100"),
        ]:
            path = path.replace(placeholder, value)
        return path

    def test_tilejson_tiles_resolve(self, app):
        from fastapi.testclient import TestClient

        client = TestClient(app)
        tilejson = client.get(
            "/rasters/layer/emit-minerals/WebMercatorQuad/tilejson.json"
        ).json()
        url = tilejson["tiles"][0]
        assert "/rasters/layer/emit-minerals/" in url
        assert client.get(self._concrete(url)).status_code == 200

    def test_wmts_templates_resolve(self, app):
        import re

        from fastapi.testclient import TestClient

        client = TestClient(app)
        xml = client.get("/rasters/layer/emit-minerals/WMTSCapabilities.xml").text
        templates = re.findall(r'template="([^"]+)"', xml)
        assert templates, "capabilities advertised no tile templates"
        for url in templates[:3]:
            assert "/rasters/layer/emit-minerals/" in url
            assert client.get(self._concrete(url)).status_code == 200
