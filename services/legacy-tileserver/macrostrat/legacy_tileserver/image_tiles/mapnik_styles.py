"""
Generate mapnik XML for each map scale.
The stylesheets are regenerated every time the server is restarted.
"""

from json import dumps
from pathlib import Path
from subprocess import CalledProcessError, check_output
from textwrap import dedent
from typing import Optional

from mapnik import Datasource

__here__ = Path(__file__).parent


def make_datasource(db_url, **kwargs):
    pg_credentials = get_credentials(db_url)
    return Datasource(
        type="postgis",
        # Don't allow connections to remain idle
        persist_connection=False,
        estimate_extent=True,
        # Connection pool size parameters (these should be globally shared)
        initial_size=1,
        max_size=10,
        **pg_credentials,
        **kwargs,
    )


def make_line_datasource(db_url, layer_id):
    line_query = create_line_query(layer_id)
    return make_datasource(
        db_url,
        table=f"({line_query}) subset",
        key_field="line_id",
        geometry_field="geom",
        extent_cache="auto",
        extent="-180,-90,180,90",
        srid="4326",
    )


def make_polygon_datasource(db_url, layer_id):
    polygon_query = create_polygon_query(layer_id)
    pg_credentials = get_credentials(db_url)
    return Datasource(
        type="postgis",
        table=f"({polygon_query}) subset",
        key_field="map_id",
        geometry_field="geom",
        extent_cache="auto",
        extent="-180,-90,180,90",
        srid="4326",
        **pg_credentials,
    )


def make_carto_stylesheet(scale, db_url):
    cartoCSS = (__here__ / "style.mss").read_text()

    webmercator_srs = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over"

    return {
        "bounds": [-89, -179, 89, 179],
        "center": [0, 0, 1],
        "format": "png8",
        "interactivity": False,
        "minzoom": 0,
        "maxzoom": 16,
        "srs": webmercator_srs,
        "Stylesheet": [{"id": "burwell", "data": cartoCSS}],
        "Layer": [
            {
                "geometry": "polygon",
                # "Datasource": {
                #     # Placeholder
                #     "type": "postgis",
                #     "table": f"PLACEHOLDER",
                #     "key_field": "map_id",
                #     "geometry_field": "geom",
                #     "extent_cache": "auto",
                #     "extent": "-179,-89,179,89",
                #     **pg_credentials,
                #     "srid": "4326",
                # },
                "id": f"units_{scale}",
                "class": "units",
                "srs-name": "WGS84",
                "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
                "advanced": {},
                "name": f"units_{scale}",
                "minZoom": "0",
                "maxZoom": "16",
            },
            {
                "geometry": "linestring",
                # "Datasource": {
                #     # Placeholder
                #     "type": "postgis",
                # },
                "id": f"lines_{scale}",
                "class": "lines",
                "srs-name": "WGS84",
                "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
                "advanced": {},
                "name": f"lines_{scale}",
                "minZoom": "0",
                "maxZoom": "16",
            },
        ],
        "scale": 2,
        "metatile": 1,
        "name": "burwell",
        "description": "burwell",
        "attribution": "Data providers, UW-Macrostrat",
    }


def make_mapnik_xml(scale, db_url=None):
    """Make a mapnik xml file for a given scale"""
    carto = make_carto_stylesheet(scale, db_url)
    # Call out to carto to convert the cartoCSS to mapnik xml
    fn = f"/tmp/carto_{scale}.mml"
    with open(fn, "w") as f:
        f.write(dumps(carto))

    try:
        return check_output(["carto", f.name]).decode("utf-8")
    except CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        raise exc


def get_credentials(db_url=None):
    if db_url is None:
        # Return template credentials
        return {
            "host": "DATABASE_HOST",
            "port": "DATABASE_PORT",
            "user": "DATABASE_USER",
            "password": "DATABASE_PASSWORD",
            "dbname": "DATABASE_NAME",
        }

    host = db_url.host
    # We can set the application ID in the host field for now,
    # revisit how this is set with Mapnik 4.0
    # https://get-map.org/mapnik-lost-manual/book/_core_data_sources.html
    host = host + " application_name=image-tileserver"

    return {
        "host": host,
        "port": db_url.port,
        "user": db_url.username,
        "password": db_url.password,
        "dbname": db_url.database,
    }


# Mapnik fills `!bbox!` (the render box, in the layer's SRID) and
# `!pixel_width!` (map units per pixel) per render, and adds no bbox filter of
# its own when the subquery carries the token. `layer_id` is the map layer of
# the carto member for the scale: NULL draws nothing, for a band carto has no
# solved member for.
def create_polygon_query(layer_id: Optional[int]) -> str:
    return dedent(
        f"""
        SELECT map_id, color, geom
        FROM tile_layers.carto_image_units(!bbox!, {_sql_int(layer_id)}, !pixel_width!)
        """
    )


def create_line_query(layer_id: Optional[int]) -> str:
    return dedent(
        f"""
        SELECT line_id, direction, type, geom
        FROM tile_layers.carto_image_lines(!bbox!, {_sql_int(layer_id)}, !pixel_width!)
        """
    )


def _sql_int(value: Optional[int]) -> str:
    return "NULL::integer" if value is None else str(int(value))
