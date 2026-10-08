"""The rendering pipeline end to end, with a real Mapnik: the CartoCSS compiles
through `carto`, loads, and draws a colored unit and a typed line into a PNG.

Needs Mapnik's Python bindings, which only the service image has, so the image
build runs this (see the Dockerfile); elsewhere it is skipped. No database: the
layers are fed from GeoJSON files in place of the PostGIS datasources.
"""

import json
import struct
import zlib
from pathlib import Path

import pytest
from morecantile import Tile

mapnik = pytest.importorskip("mapnik")

from macrostrat.legacy_tileserver.image_tiles import render_tile  # noqa: E402
from macrostrat.legacy_tileserver.image_tiles.mapnik_styles import (  # noqa: E402
    make_mapnik_xml,
)

SCALE = "small"
TILE = Tile(x=1, y=0, z=1)  # longitude 0..180, latitude 0..85
UNIT_COLOR = "#0000ff"
# Inside the tile, with a margin, so the center pixel is well within the unit.
UNIT_COORDS = [[[20, 10], [160, 10], [160, 75], [20, 75], [20, 10]]]
LINE_COORDS = [[20, 40], [160, 40]]


def geojson(path: Path, geometry: dict, properties: dict) -> Path:
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": geometry, "properties": properties}
                ],
            }
        )
    )
    return path


def load_map(tmp_path, with_line: bool) -> "mapnik.Map":
    units = geojson(
        tmp_path / "units.geojson",
        {"type": "Polygon", "coordinates": UNIT_COORDS},
        {"map_id": 1, "color": UNIT_COLOR},
    )
    lines = geojson(
        tmp_path / "lines.geojson",
        {"type": "LineString", "coordinates": LINE_COORDS if with_line else []},
        {"line_id": 1, "type": "dike", "direction": ""},
    )
    _map = mapnik.Map(512, 512)
    mapnik.load_map_from_string(_map, make_mapnik_xml(SCALE))
    for layer in _map.layers:
        if layer.name == f"units_{SCALE}":
            layer.datasource = mapnik.Datasource(type="geojson", file=str(units))
        elif layer.name == f"lines_{SCALE}":
            layer.datasource = mapnik.Datasource(type="geojson", file=str(lines))
    return _map


def png_pixels(png: bytes) -> tuple[int, int, bytes]:
    """Decode an 8-bit RGBA PNG without filtering tricks: (width, height, rgba)."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        kind = png[pos + 4 : pos + 8]
        data = png[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", data[:10])
            assert (depth, color_type) == (8, 6), "expected 8-bit RGBA"
        elif kind == b"IDAT":
            idat += data
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    rows, prev = [], bytearray(stride)
    for y in range(height):
        f = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        for i in range(stride):
            a = row[i - 4] if i >= 4 else 0
            b = prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if f == 1:
                row[i] = (row[i] + a) & 0xFF
            elif f == 2:
                row[i] = (row[i] + b) & 0xFF
            elif f == 3:
                row[i] = (row[i] + (a + b) // 2) & 0xFF
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                row[i] = (row[i] + pred) & 0xFF
        rows.append(bytes(row))
        prev = row
    return width, height, b"".join(rows)


def pixel(rgba: bytes, width: int, x: int, y: int) -> tuple[int, int, int, int]:
    i = 4 * (y * width + x)
    return tuple(rgba[i : i + 4])


def test_cartocss_compiles_and_draws_a_unit_in_its_color(tmp_path):
    png = render_tile(load_map(tmp_path, with_line=False), TILE)
    width, height, rgba = png_pixels(png)
    assert (width, height) == (512, 512)
    # Inside the unit: its legend color, opaque. Outside: nothing drawn.
    assert pixel(rgba, width, 256, 256) == (0, 0, 255, 255)
    assert pixel(rgba, width, 2, 2)[3] == 0


def test_a_typed_line_is_drawn(tmp_path):
    without = png_pixels(render_tile(load_map(tmp_path, with_line=False), TILE))[2]
    with_line = png_pixels(render_tile(load_map(tmp_path, with_line=True), TILE))[2]
    changed = sum(
        1
        for i in range(0, len(without), 4)
        if without[i : i + 4] != with_line[i : i + 4]
    )
    # A line across the unit touches at least its own length in pixels.
    assert changed > 200
