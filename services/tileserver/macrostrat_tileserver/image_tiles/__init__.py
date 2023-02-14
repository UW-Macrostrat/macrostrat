from fastapi import FastAPI, Response
from morecantile import Tile, tms
from mapnik import Map, load_map_from_string, Image, render, Box2d
from pathlib import Path
from timvt.settings import TileSettings
import time
from .convert import make_mapnik_xml
from .config import scales, scale_zooms, scale_for_zoom

tile_settings = TileSettings()


mapnik_layers = FastAPI()

layer_cache = {}


def build_layer_cache():
    ## Generate mapnik XML files
    for scale in scales:
        # Log timings
        t = time.time()
        layer_cache[scale] = make_mapnik_xml(scale)
        print(f"Generated mapnik XML for scale {scale} in {time.time() - t} seconds")


@mapnik_layers.get("/carto-image/{z}/{x}/{y}.png")
async def root(z: int, x: int, y: int):
    quad = tms.get("WebMercatorQuad")
    tile = Tile(x, y, z)
    bbox = quad.xy_bounds(tile)

    # Get map scale for this zoom level
    scale = scale_for_zoom(z)

    # Path to mapnik XML file

    # Load mapnik XML
    map = Map(512, 512)
    load_map_from_string(map, layer_cache[scale])
    # Set bbox of map

    # map.zoom_all()

    box = Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom)
    map.zoom_to_box(box)

    # Render map to image
    im = Image(512, 512)
    render(map, im)
    # Return image as binary
    img = im.tostring("png")
    return Response(img, media_type="image/png")
