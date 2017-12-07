from .base import Base
import sys
import datetime
from psycopg2.extensions import AsIs
from tiletanic import tilecover
from shapely import geometry
from shapely.wkt import loads
from tiletanic import tileschemes
from urlparse import urlparse
from threading import Thread
import requests
from Queue import Queue
from tqdm import *
class ParallelRequests():
    concurrency = 5
    fails = []

    def __init__(self, urls, headers):
        self.urls = urls
        self.headers = headers
        self.q = Queue(self.concurrency * 2)
        self.fails = []
        self.done = 0

        for i in range(self.concurrency):
            t = Thread(target=self.make_request)
            t.daemon = True
            t.start()

        for url in urls:
            self.q.put(url)

        self.q.join()
        if len(self.fails) > 0:
            print 'FAILS - ', self.fails


    def make_request(self):
        while True:
            url = self.q.get()
            r = requests.get(url, headers=self.headers)
            if r.status_code != 200 and r.status_code != 204:
                print r.status_code
                self.fails.append(url)

            self.q.task_done()



class Seed(Base):
    '''
    macrostrat seed <source_id or scale>:
        Seed the tileserver

    Usage:
      macrostrat seed 123
      macrostrat schlep -h | --help
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
    #layers = [ 'carto', 'tiny', 'small', 'medium', 'large']
    layers = [ 'carto' ]
    min_zooms = {
        'carto': 0,
        'tiny': 0,
        'small': 2,
        'medium': 4,
        'large': 9
    }


    @classmethod
    def make_polygon(self, min, max):
        return loads('POLYGON((%s %s, %s %s, %s %s, %s %s, %s %s))' % (min[0], min[1], min[0], max[1], max[0], max[1], max[0], min[1], min[0], min[1]))

    @classmethod
    def chunk_area(self, area):
        envelope = area.envelope
        centroid = envelope.centroid

        q1 = Seed.make_polygon([envelope.bounds[0], envelope.bounds[1]], [centroid.x, centroid.y])
        q2 = Seed.make_polygon([envelope.bounds[0], centroid.y], [centroid.x, envelope.bounds[3]])
        q3 = Seed.make_polygon([centroid.x, centroid.y], [envelope.bounds[2], envelope.bounds[3]])
        q4 = Seed.make_polygon([centroid.x, envelope.bounds[1]], [envelope.bounds[2], centroid.y])

        extents = []
        for q in [ q1, q2, q3, q4 ]:
            _c = q.centroid

            # Get extent
            extent = q.bounds;

            a = Seed.make_polygon([extent[0], extent[1]], [_c.x, _c.y]).intersection(area)
            b = Seed.make_polygon([extent[0], _c.y], [_c.x, extent[3]]).intersection(area)
            c = Seed.make_polygon([_c.x, _c.y], [extent[2], extent[3]]).intersection(area)
            d = Seed.make_polygon([_c.x, extent[1]], [extent[2], _c.y]).intersection(area)

            for piece in [ a, b, c, d ]:
                if not piece.is_empty:
                    extents.append(piece)

        return extents

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
        #tiles = [ t for t in tilecover.cover_geometry(tiler, seed_area, 11) ]
        #print tiles
        # parts = self.chunk_area(seed_area)
        #
        # deleted_tiles = []
        # seeded_tiles = []
        # for idx, part in enumerate(parts):
        #     print idx
        #     for z in self.cached_zooms:
        #         tiles = [ t for t in tilecover.cover_geometry(tiler, part, z) ]
        #         for tile in tiles:
        #             if '%s|%s|%s' % (tile.z, tile.x, tile.y) not in deleted_tiles:
        #                 deleted_tiles.append('%s|%s|%s' % (tile.z, tile.x, tile.y))
        #             else:
        #                 tiles.remove(tile)
        #
        #         # Call delete tile
        #         for layer in self.layers:
        #             ParallelRequests([ 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y) for tile in tiles ], { 'X-Tilestrata-DeleteTile': self.credentials['tileserver_secret'] })
        #     for z in self.zooms:
        #         tiles = [ t for t in tilecover.cover_geometry(tiler, part, z) ]
        #         for tile in tiles:
        #             if '%s|%s|%s' % (tile.z, tile.x, tile.y) not in seeded_tiles:
        #                 seeded_tiles.append('%s|%s|%s' % (tile.z, tile.x, tile.y))
        #             else:
        #                 tiles.remove(tile)
        #
        #         # Request that a tile be created
        #         for layer in self.layers:
        #             ParallelRequests([ 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y) for tile in tiles ], { 'X-Tilestrata-SkipCache': '*'})
        #


        print '     Deleting...'
        for z in self.cached_zooms:
            print '         ', z
            tiles = [ t for t in tilecover.cover_geometry(tiler, seed_area, z) ]
            headers = { 'X-Tilestrata-DeleteTile': self.credentials['tileserver_secret'] }
            # Call delete tile
            for layer in self.layers:
                for tile in tqdm(tiles):
                    url = 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y)
                    r = requests.get(url, headers=headers)
                    if r.status_code != 200 and r.status_code != 204:
                        print r.status_code
                        # fails.append(url)

                # ParallelRequests([ 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y) for tile in tiles ], { 'X-Tilestrata-DeleteTile': self.credentials['tileserver_secret'] })

        print '     Seeding...'
        for z in self.zooms:
            print '         ', z
            tiles = [ t for t in tilecover.cover_geometry(tiler, seed_area, z) ]
            headers = { 'X-Tilestrata-SkipCache': '*'}
            # Request that a tile be created
            for layer in self.layers:
                for tile in tqdm(tiles):
                    url = 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y)
                    r = requests.get(url, headers=headers)
                    if r.status_code != 200 and r.status_code != 204:
                        print r.status_code
                        # fails.append(url)
                # ParallelRequests([ 'http://localhost:5555/%s/%s/%s/%s.png' % (layer, tile.z, tile.x, tile.y) for tile in tiles ], { 'X-Tilestrata-SkipCache': '*'})
