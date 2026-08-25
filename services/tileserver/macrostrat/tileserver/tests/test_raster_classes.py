"""Macrostrat's `?classes=` shorthand on categorical raster layers.

The filtering itself belongs to `macrostrat.raster_layers` and is tested there.
What's Macrostrat-specific — and so tested here — is the flat query parameter
this tile server layers on top of it, and the fact that adding it doesn't cost
the generic `?algorithm=` form.
"""

import pytest

from macrostrat.tileserver.rasters import (
    _class_filter_dependency,
    _layer_router,
    raster_layer_configs,
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
        config = raster_layer_configs()[0]

        app = FastAPI()
        app.include_router(_layer_router(config, index), prefix="/rasters/test")
        paths = app.openapi()["paths"]
        path = "/rasters/test/tiles/{tileMatrixSetId}/{z}/{x}/{y}@{scale}x.{format}"
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
        from macrostrat.tileserver.rasters import _supported_tms

        assert _supported_tms().list() == ["WebMercatorQuad"]

    def test_other_grids_are_rejected(self, app):
        from fastapi.testclient import TestClient

        client = TestClient(app)
        path = "/rasters/emit-minerals/tiles/{tms}/8/44/100@2x.png"
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

    class FakeIndex:
        def __init__(self, categories):
            self._categories = categories
            self.asked = []

        def get_categories(self, layer):
            self.asked.append(layer)
            return self._categories

    def test_one_render_per_class(self):
        from macrostrat.tileserver.rasters import _class_renders

        index = self.FakeIndex([self.FakeCategory("Alunite"), self.FakeCategory("Kaolin")])
        renders = _class_renders(index, ["emit-minerals"])(None)
        assert renders == {
            "Alunite": {"classes": "Alunite"},
            "Kaolin": {"classes": "Kaolin"},
        }

    def test_no_vocabulary_means_no_extra_layers(self):
        """A layer without class names still gets WMTS, just the one layer."""
        from macrostrat.tileserver.rasters import _class_renders

        assert _class_renders(self.FakeIndex([]), ["emit-minerals"])(None) == {}

    def test_vocabulary_is_read_per_request(self):
        """So classes added later appear without restarting the tile server."""
        from macrostrat.tileserver.rasters import _class_renders

        index = self.FakeIndex([self.FakeCategory("Alunite")])
        get_renders = _class_renders(index, ["emit-minerals"])
        get_renders(None)
        get_renders(None)
        assert index.asked == ["emit-minerals", "emit-minerals"]

    def test_capabilities_route_is_registered(self, app):
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/rasters/emit-minerals/WMTSCapabilities.xml" in paths
