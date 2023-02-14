"""
Generate mapnik XML on the fly for each map scale.
The stylesheets are regenerated every time the server is restarted.
"""
from os import environ
from macrostrat.database import Database
from pathlib import Path
from subprocess import check_output, CalledProcessError
from json import dumps
from .config import layer_order
from functools import lru_cache

db = Database(environ.get("DATABASE_URL"))


def make_carto_stylesheet(scale):
    engine = db.engine

    pg_credentials = {
        "host": engine.url.host,
        "port": engine.url.port,
        "user": engine.url.username,
        "password": engine.url.password,
        "dbname": engine.url.database,
    }

    line_sql = " UNION ALL ".join(
        f"SELECT * FROM lines.{s}" for s in layer_order[scale]
    )

    __here__ = Path(__file__).parent
    cartoCSS = (__here__ / "styles" / "base-styles.mss").read_text()

    cartoCSS += build_color_styles()

    return {
        "bounds": [-89, -179, 89, 179],
        "center": [0, 0, 1],
        "format": "png8",
        "interactivity": False,
        "minzoom": 0,
        "maxzoom": 16,
        "srs": "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over",
        "Stylesheet": [{"id": "burwell", "data": cartoCSS}],
        "Layer": [
            {
                "geometry": "polygon",
                "Datasource": {
                    "type": "postgis",
                    "table": f"(SELECT z.map_id, COALESCE(l.color, '#777777') AS color, z.geom FROM carto_new.{scale} z LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id LEFT JOIN maps.sources ON l.source_id = sources.source_id WHERE sources.status_code = 'active') subset",
                    "key_field": "map_id",
                    "geometry_field": "geom",
                    "extent_cache": "auto",
                    "extent": "-179,-89,179,89",
                    **pg_credentials,
                    "srid": "4326",
                },
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
                "Datasource": {
                    "type": "postgis",
                    "table": f"(SELECT x.line_id, x.geom, q.direction, q.type FROM carto_new.lines_{scale} x LEFT JOIN ( {line_sql} ) q on q.line_id = x.line_id LEFT JOIN maps.sources ON x.source_id = sources.source_id WHERE sources.status_code = 'active') subset",
                    "key_field": "line_id",
                    "geometry_field": "geom",
                    "extent_cache": "auto",
                    "extent": "-179,-89,179,89",
                    **pg_credentials,
                    "srid": "4326",
                },
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
        "scale": 1,
        "metatile": 2,
        "name": "burwell",
        "description": "burwell",
        "attribution": "Data providers, UW-Macrostrat",
    }


# Cache the result of this function
@lru_cache(maxsize=1)
def build_color_styles():
    # res = db.session.execute(
    #     "SELECT DISTINCT color FROM maps.legend WHERE color IS NOT NULL AND color != ''"
    # )

    mss = ""
    # for row in res:
    mss += f"""
    .units {{
        polygon-fill: [color];
    }}
    """
    return mss


def make_mapnik_xml(scale):
    """Make a mapnik xml file for a given scale"""
    carto = make_carto_stylesheet(scale)
    # Call out to carto to convert the cartoCSS to mapnik xml
    fn = f"/tmp/carto_{scale}.mml"
    with open(fn, "w") as f:
        f.write(dumps(carto))

    try:
        return check_output(["carto", fn]).decode("utf-8")
    except CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        raise exc
