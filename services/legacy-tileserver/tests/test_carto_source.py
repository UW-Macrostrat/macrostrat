"""`LEGACY_CARTO_FROM_COMPILATION` selects what image tiles are drawn from.

Imports Mapnik through the package, so it runs in the image build only.
"""

import pytest

pytest.importorskip("mapnik")

from macrostrat.legacy_tileserver.image_tiles.config import (  # noqa: E402
    LEGACY_BANDS,
    ScaleBands,
    carto_from_compilation,
)
from macrostrat.legacy_tileserver.image_tiles.mapnik_styles import (  # noqa: E402
    create_line_query,
    create_polygon_query,
)


@pytest.mark.parametrize(
    "value, expected",
    [(None, False), ("", False), ("false", False), ("0", False), ("true", True)],
)
def test_switch_is_off_unless_set(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("LEGACY_CARTO_FROM_COMPILATION", raising=False)
    else:
        monkeypatch.setenv("LEGACY_CARTO_FROM_COMPILATION", value)
    assert carto_from_compilation() is expected


def test_legacy_bands_are_served_as_before():
    bands = ScaleBands(LEGACY_BANDS)
    scales = [bands.scale_for_zoom(z) for z in (0, 2, 3, 5, 6, 9, 10, 16)]
    assert scales == [
        "tiny",
        "tiny",
        "small",
        "small",
        "medium",
        "medium",
        "large",
        "large",
    ]


def test_legacy_queries_read_the_carto_tables():
    polygons = create_polygon_query("medium", 6, from_compilation=False)
    lines = create_line_query("medium", 6, from_compilation=False)
    assert "FROM carto.polygons" in polygons and "z.scale = 'medium'" in polygons
    assert "FROM carto.lines" in lines and "x.scale = 'medium'" in lines
    assert "tile_layers" not in polygons + lines


def test_compilation_queries_pass_the_band_zoom():
    polygons = create_polygon_query("medium", 6, from_compilation=True)
    lines = create_line_query("medium", 6, from_compilation=True)
    assert "tile_layers.carto_image_units(!bbox!, 6, !pixel_width!)" in polygons
    assert "tile_layers.carto_image_lines(!bbox!, 6, !pixel_width!)" in lines
    assert "carto." not in polygons.replace("carto_image", "")
