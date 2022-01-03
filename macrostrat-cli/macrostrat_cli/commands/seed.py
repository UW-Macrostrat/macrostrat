from .base import Base
import sys
import datetime
from tiletanic import tilecover
from shapely import geometry
from shapely.wkt import loads
from tiletanic import tileschemes
import requests
from tqdm import *
from subprocess import call
import os
import sqlite3
from multiprocessing.pool import Pool
from .. import config as cfg
from ..database import get_pg_credentials

THREADS = 4
FNULL = open(os.devnull, "w")

# Used for making requests to the seed server
def http_request(params):
    url, headers = params
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200 and r.status_code != 204:
            print("Bad request to tileserver %s" % (r.status_code,))
            sys.exit()
    except:
        pass


class Seed(Base):
    """
    macrostrat seed <source_id, scale, layer, or all>:
        Seed vector and raster tiles. When providing a <source_id> only
        raster tiles will be seeded. To seed vector tiles a <layer> must be
        provided (carto or carto-slim). Vector tile seeding requires recreating
        all tiles and takes a few hours, so using tmux or screen is advisable.

        To reseed all tiles you can run `macrostrat seed all`

    Usage:
      macrostrat seed 123
      macrostrat seed tiny
      macrostrat seed carto-slim
      macrostrat seed -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat seed 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    zooms = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    cached_zooms = [11, 12, 13]

    layers = ["carto"]
    min_zooms = {"carto": 0, "tiny": 0, "small": 2, "medium": 4, "large": 9}

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def seed_pbdb_collections(self):
        p = Pool(THREADS)

        tiler = tileschemes.WebMercator()
        # For now seed the whole world...
        self.pg["cursor"].execute(
            """
            SELECT ST_AsText(ST_Transform(
                ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326)
            , 3857)) as geom
        """
        )
        source = self.pg["cursor"].fetchone()
        seed_area = loads(source[0])

        headers = {"X-Tilestrata-SkipCache": "*"}

        secret = cfg.TILESERVER_SECRET
        if secret is None:
            raise AttributeError("TILESERVER_SECRET must be defined")

        for z in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            tiles = [
                (
                    "http://localhost:8675/pbdb-collections/%s/%s/%s.mvt?secret=%s"
                    % (tile.z, tile.x, tile.y, secret),
                    headers,
                )
                for tile in tilecover.cover_geometry(tiler, seed_area, z)
            ]

            # Throw the seed requests at the multiprocessing pool
            r = list(tqdm(p.imap(http_request, tiles), total=len(tiles)))

    # Currently this doesn't operate on a source basis. It is all or nothing.
    def seed_mbtiles(self, layer):
        mbtile_path = cfg.MBTILES_PATH
        path = os.path.dirname(__file__)

        # Delete existing scale mbtiles files
        for scale in ["tiny", "small", "medium", "large"]:
            call(
                [f"rm {mbtile_path}/tiny.mbtiles"],
                shell=True,
                stdout=FNULL,
            )

        url = get_pg_credentials()
        pg_args = (url.host, url.port, url.database, url.username)

        # Create tiles for tiny
        call(
            [
                'tippecanoe -o %s/tiny.mbtiles --minimum-zoom=0 --maximum-zoom=2 --generate-ids --detect-shared-borders --simplification=5 -Lunits:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`") -Llines:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`")'
                % (
                    mbtile_path,
                    *pg_args,
                    "%s/seed_scripts/sql/%s/tiny.sql"
                    % (
                        path,
                        layer,
                    ),
                    *pg_args,
                    "%s/seed_scripts/sql/%s/tiny_lines.sql"
                    % (
                        path,
                        layer,
                    ),
                )
            ],
            shell=True,
            stdout=FNULL,
            executable="/bin/bash",
        )

        # Create tiles for small
        call(
            [
                'tippecanoe -o %s/small.mbtiles --minimum-zoom=3 --maximum-zoom=5 --generate-ids --detect-shared-borders --simplification=6 -Lunits:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`") -Llines:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`")'
                % (
                    mbtile_path,
                    *pg_args,
                    "%s/seed_scripts/sql/%s/small.sql"
                    % (
                        path,
                        layer,
                    ),
                    *pg_args,
                    "%s/seed_scripts/sql/%s/small_lines.sql"
                    % (
                        path,
                        layer,
                    ),
                )
            ],
            shell=True,
            stdout=FNULL,
            executable="/bin/bash",
        )

        # Create tiles for medium
        call(
            [
                'tippecanoe -o %s/medium.mbtiles --minimum-zoom=6 --maximum-zoom=8 --generate-ids --detect-shared-borders --simplification=7 -Lunits:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`") -Llines:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`")'
                % (
                    mbtile_path,
                    *pg_args,
                    "%s/seed_scripts/sql/%s/medium.sql"
                    % (
                        path,
                        layer,
                    ),
                    *pg_args,
                    "%s/seed_scripts/sql/%s/medium_lines.sql"
                    % (
                        path,
                        layer,
                    ),
                )
            ],
            shell=True,
            stdout=FNULL,
            executable="/bin/bash",
        )

        # Create tiles for large
        call(
            [
                'tippecanoe -o %s/large.mbtiles --minimum-zoom=9 --maximum-zoom=12 --generate-ids --detect-shared-borders --simplification=4 -Lunits:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`") -Llines:<(ogr2ogr -f "GeoJSON" /dev/stdout "PG:host=%s port=%s dbname=%s user=%s" -sql "`cat %s`")'
                % (
                    mbtile_path,
                    *pg_args,
                    "%s/seed_scripts/sql/%s/large.sql"
                    % (
                        path,
                        layer,
                    ),
                    *pg_args,
                    "%s/seed_scripts/sql/%s/large_lines.sql"
                    % (
                        path,
                        layer,
                    ),
                )
            ],
            shell=True,
            stdout=FNULL,
            executable="/bin/bash",
        )

        # Connect to the sink (i.e. sqlite/mbtiles database)
        sink_connection = sqlite3.connect(
            "%s/%s.mbtiles"
            % (
                mbtile_path,
                layer,
            )
        )
        sink_cursor = sink_connection.cursor()

        # Check if this is an existing mbtiles file or not
        sink_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'"
        )
        metadata_exists = sink_cursor.fetchone()

        if metadata_exists is None:
            with open("%s/seed_scripts/json_schema.json" % (path,), "r") as in_schema:
                schema = in_schema.read()
                sink_cursor.execute(
                    """
                    CREATE TABLE metadata (name text, value text);
                """
                )
                metadata = [
                    ("name", layer),
                    ("format", "pbf"),
                    ("bounds", "-180.0,-85,180,85"),
                    ("center", "0,0"),
                    ("minzoom", 0),
                    ("maxzoom", 16),
                    ("attribution", "Macrostrat, 2018"),
                    ("type", "overlay"),
                    ("version", "2.0"),
                    ("json", schema),
                ]
                sink_cursor.executemany(
                    """
                    INSERT INTO metadata (name, value)
                    VALUES (?, ?);
                """,
                    metadata,
                )
                sink_cursor.execute(
                    """
                    CREATE TABLE tiles (
                        zoom_level integer,
                        tile_column integer,
                        tile_row integer,
                        tile_data blob
                    );
                """
                )
                sink_cursor.execute(
                    """
                    CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row);
                """
                )
                sink_connection.commit()

        # Merge the mbtiles files created by Tippecanoe
        # Need to run in this order to get proper stacking!
        print("Merging mbtiles files...")
        for scale in ["large", "medium", "small", "tiny"]:
            # Connect to the source
            source_connection = sqlite3.connect(
                "%s/%s.mbtiles"
                % (
                    mbtile_path,
                    scale,
                )
            )
            source_cursor = source_connection.cursor()

            for tile in source_cursor.execute(
                "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles"
            ):
                sink_cursor.execute(
                    """
                    INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data)
                    VALUES (?, ?, ?, ?)
                """,
                    tile,
                )
            sink_connection.commit()
            source_connection.close()

        sink_connection.close()

    def seed_raster(self):
        # For now seed the whole world...
        self.pg["cursor"].execute(
            """
            SELECT ST_AsText(ST_Transform(
                ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326)
            , 3857)) as geom
        """
        )
        source = self.pg["cursor"].fetchone()
        seed_area = loads(source[0])

        tiler = tileschemes.WebMercator()

        print("     Seeding raster tiles...")
        fails = 0

        # Create a multiprocessing pool for parallel http requests
        p = Pool(THREADS)

        # Update the raster tiles
        headers = {"X-Tilestrata-SkipCache": "*"}
        for z in self.zooms:
            tiles = [
                (
                    "http://localhost:8675/carto/%s/%s/%s.png?secret=%s"
                    % (tile.z, tile.x, tile.y, self.credentials["tileserver_secret"]),
                    headers,
                )
                for tile in tilecover.cover_geometry(tiler, seed_area, z)
            ]
            r = list(tqdm(p.imap(http_request, tiles), total=len(tiles)))

    def run(self):
        scales = ["tiny", "small", "medium", "large"]
        # Check if a command was provided
        if len(self.args) == 1:
            print("Please specify a source_id or scale")
            sys.exit()

        if self.args[1] == "all":
            print("  Working on carto (vector)")
            Seed.seed_mbtiles(self, "carto")

            print("  Working on carto-slim (vector)")
            Seed.seed_mbtiles(self, "carto-slim")

            print("  Working on carto (raster)")
            Seed.seed_raster(self)

            print(
                """
                All tiles have been rerolled. If you are experiencing rendering
                issues try the following:
                  + Restart the tileserver (`pm2 restart tileserver`)
                  + Clear the cache (`redis-cli flushdb`)

                If you are experiencing issues related to the coloring of raster
                tiles try restarting the seed server and rerolling:

                  pm2 restart seed-server && macrostrat seed carto-raster

                To move these tiles into production, run the following:

                    scp /data/projects/tileserver/seeder/carto.mbtiles strata:/data/tmp
                    scp /data/projects/tileserver/seeder/carto-slim.mbtiles strata:/data/tmp
                    scp /data/projects/tileserver/seeder/carto-raster.mbtiles strata:/data/tmp

            """
            )
            sys.exit()

        if self.args[1] == "carto" or self.args[1] == "carto-slim":
            Seed.seed_mbtiles(self, self.args[1])
            sys.exit()

        if self.args[1] == "carto-raster":
            Seed.seed_raster(self)
            sys.exit()

        if self.args[1] == "pbdb-collections":
            Seed.seed_pbdb_collections(self)
            sys.exit()

        seed_area = None
        # Check if it is a source_id
        if self.args[1].isdigit():
            # Make sure it is a valid source_id
            self.pg["cursor"].execute(
                """
                SELECT ST_AsText(ST_Transform(
                    ST_Intersection(
                        ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326),
                        ST_SetSRID(rgeom, 4326)
                    )
                , 3857)) as geom,
                ST_AsText(web_geom) AS web_geom,
                display_scales
                FROM maps.sources
                WHERE source_id = %(source_id)s
            """,
                {"source_id": self.args[1]},
            )
            source = self.pg["cursor"].fetchone()

            if source is None:
                print("Source ID %s was not found" % (self.args[1],))
                sys.exit()
            if source[0] is None:
                print(
                    "Source ID %s is missing an rgeom. Please run `macrostrat process web_geom %s` to create it"
                    % (
                        source_id,
                        source_id,
                    )
                )
                sys.exit()

            seed_area = loads(source[0])

        else:
            if self.args[1] not in scales:
                print("Invalid scale")
                sys.exit()

        tiler = tileschemes.WebMercator()

        print("     Seeding raster tiles...")
        fails = 0
        # Update the raster version of the tiles
        tiler = tileschemes.WebMercator()
        seed_area = loads(source[0])

        # Create a multiprocessing pool for parallel http requests
        p = Pool(THREADS)

        # Update the raster tiles
        headers = {"X-Tilestrata-SkipCache": "*"}
        for z in self.zooms:
            tiles = [
                (
                    "http://localhost:8675/carto/%s/%s/%s.png?secret=%s"
                    % (tile.z, tile.x, tile.y, self.credentials["tileserver_secret"]),
                    headers,
                )
                for tile in tilecover.cover_geometry(tiler, seed_area, z)
            ]

            # Throw the delete requests at the multiprocessing pool
            r = list(tqdm(p.imap(http_request, tiles), total=len(tiles)))

        print("     Deleting...")
        headers = {"X-Tilestrata-DeleteTile": self.credentials["tileserver_secret"]}
        for z in self.cached_zooms:
            print("         ", z)
            tiles = [
                (
                    "http://localhost:5555/carto/%s/%s/%s.png"
                    % (tile.z, tile.x, tile.y),
                    headers,
                )
                for tile in tilecover.cover_geometry(tiler, seed_area, z)
            ]

            # Throw the delete requests at the multiprocessing pool
            r = list(tqdm(p.imap(http_request, tiles), total=len(tiles)))
