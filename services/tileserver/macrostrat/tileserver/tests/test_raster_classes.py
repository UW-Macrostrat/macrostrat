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
