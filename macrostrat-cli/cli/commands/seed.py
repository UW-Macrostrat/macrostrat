from .base import Base
import sys
import datetime
from tiletanic import tilecover
from shapely import geometry
from shapely.wkt import loads
from tiletanic import tileschemes
import requests
from tqdm import *


class Seed(Base):
    '''
    macrostrat seed <source_id or scale>:
        Seed the tileserver

    Usage:
      macrostrat seed 123
      macrostrat seed -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat seed 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    '''

    zooms = [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ]
    cached_zooms = [ 11, 12, 13 ]

    layers = [ 'carto' ]
    min_zooms = {
        'carto': 0,
        'tiny': 0,
        'small': 2,
        'medium': 4,
        'large': 9
    }

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def run(self):
        scales = ['tiny', 'small', 'medium', 'large']
        # Check if a command was provided
        if len(self.args) == 1:
            print 'Please specify a source_id or scale'
            sys.exit()

        seed_area = None
        # Check if it is a source_id
        if self.args[1].isdigit():
            # Make sure it is a valid source_id
            self.pg['cursor'].execute("""
                SELECT ST_AsText(ST_Transform(
                    ST_Intersection(
                        ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326),
                        ST_SetSRID(rgeom, 4326)
                    )
                , 3857)) as geom,
                display_scales
                FROM maps.sources
                WHERE source_id = %(source_id)s
            """, { 'source_id': self.args[1] })
            source = self.pg['cursor'].fetchone()

            if source is None:
                print 'Source ID %s was not found' % (self.args[1], )
                sys.exit()
            if source[0] is None:
                print 'Source ID %s is missing an rgeom. Please run `macrostrat process web_geom %s` to create it' % (source_id, source_id, )
                sys.exit()

            seed_area = loads(source[0])

        else:
            if self.args[1] not in scales:
                print 'Invalid scale'
                sys.exit()


        tiler = tileschemes.WebMercator()

        print '     Seeding...'
        for z in self.zooms:
            print '         ', z
            tiles = [ t for t in tilecover.cover_geometry(tiler, seed_area, z) ]
            headers = { 'X-Tilestrata-SkipCache': '*'}
            # Request that a tile be created
            for layer in self.layers:
                for tile in tqdm(tiles):
                    url = 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y)
                    try:
                        r = requests.get(url, headers=headers)
                        if r.status_code != 200 and r.status_code != 204:
                            print r.status_code
                    except:
                        pass

        print '     Deleting...'
        for z in self.cached_zooms:
            print '         ', z
            tiles = [ t for t in tilecover.cover_geometry(tiler, seed_area, z) ]
            headers = { 'X-Tilestrata-DeleteTile': self.credentials['tileserver_secret'] }
            # Call delete tile
            for layer in self.layers:
                for tile in tqdm(tiles):
                    url = 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y)
                    try:
                        r = requests.get(url, headers=headers)
                        if r.status_code != 200 and r.status_code != 204:
                            print r.status_code
                    except:
                        pass
                        # fails.append(url)
