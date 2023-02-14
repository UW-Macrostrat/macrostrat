from fastapi import FastAPI, Response
import morecantile
from mapnik import Map, load_map, Image, render, Box2d
from pathlib import Path
from timvt.settings import TileSettings

tile_settings = TileSettings()


mapnik_layers = FastAPI()

@mapnik_layers.get("/carto-image/{z}/{x}/{y}.png")
async def root(z: int, x: int, y: int):
    tms = morecantile.tms.get("WebMercatorQuad")

    tile = tms.tile(x, y, z)

    bbox = tms.xy_bounds(tile)

    # Path to mapnik XML file
    __here__ = Path(__file__).parent
    mapnik_xml = __here__ / "mapnik-layers" / "tiny.xml"

    # Load mapnik XML
    map = Map(256, 256)
    load_map(map, str(mapnik_xml))
    # Set bbox of map

    #map.zoom_all()

    box = Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom)
    map.zoom_to_box(box)

    # Render map to image
    im = Image(256, 256)
    render(map, im)
    # Return image as binary
    img = im.tostring("png")
    return Response(img, media_type="image/png")