import sys, os, time
import argparse

from fiona import collection
from shapely.geometry import mapping, shape
from shapely.wkt import loads, dumps
from shapely.ops import cascaded_union
from collections import OrderedDict

import multiprocessing
from multiprocessor import *

import psycopg2
from psycopg2.extensions import AsIs

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
cursor = connection.cursor()


parser = argparse.ArgumentParser(
    description="Creat a unioned reference geometry for a given source",
    epilog="Example usage: python union.py 1")

parser.add_argument(nargs="?", dest="source_id",
    default="0", type=int,
    help="The ID of the desired source to union")

arguments = parser.parse_args()

if arguments.source_id == 0:
    sys.exit(1)

vertex_max = 10000000

if __name__ == '__main__':
    start = time.time()

    tasks = multiprocessing.JoinableQueue()
    results = multiprocessing.Queue()
    all_results = []
    num_processors = multiprocessing.cpu_count() - 2
    processors = [Processor(tasks, results) for i in xrange(num_processors)]

    for each in processors:
        each.start()

    groups = []

    cursor.execute("""
        SELECT scale, name
        FROM maps.sources
        WHERE source_id = %(source_id)s
    """, {
        "source_id": arguments.source_id
    })

    result = cursor.fetchone()

    scale = result[0]

    print 'Fetching geometry for ', result[1]

    # Get all polygons of a source (Ontario)
    cursor.execute("""
        SELECT ST_NPoints(geom) vertices, ST_AsText(geom)
        FROM maps.%(scale)s
        WHERE source_id = %(source_id)s
    """, {
        "scale": AsIs(scale),
        "source_id": arguments.source_id
    })

    polygons = cursor.fetchall()

    sum_vertices = sum([ int(poly[0]) for poly in polygons ])

    print 'Total vertices - ', sum_vertices

    if sum_vertices > vertex_max:
        current_group_vertices = 0
        current_group = []
        vertices_accounted_for = 0

        for poly in polygons:
            encoded = loads(poly[1]).buffer(0)

            if current_group_vertices + poly[0] > vertex_max:
                groups.append(current_group)
                current_group = []
                current_group_vertices = 0

            current_group.append(encoded)
            current_group_vertices += poly[0]
            vertices_accounted_for += poly[0]

        groups.append(current_group)


    else:
        groups.append([ loads(poly[1]) for poly in polygons ])

    print 'Total groups - ', len(groups)
    jobs = len(groups)

    for group in groups:
        tasks.put(Task(group))

    for i in range(num_processors):
        tasks.put(None)

    while jobs:
        all_results.append(results.get())
        jobs -= 1

    print 'Done unioning groups'
    
    done = cascaded_union(all_results)

    cursor.execute("""
        UPDATE maps.sources
        SET rgeom = %(geom)s::geometry
        WHERE source_id = %(source_id)s
    """, {
        "geom": done.wkt,
        "source_id": arguments.source_id
    })
    connection.commit()

    end = time.time()

    print 'Done in ', int(end - start), 's'

'''
    schema = {
        'geometry': 'Polygon',
        'properties': OrderedDict([(u'name', 'str:254')])
    }

    print 'Writing shapefile output'

    with collection("output.shp", "w", "ESRI Shapefile", schema) as output:
        output.write({
            'properties': {
                'name': 'Ontario'
            },
            'geometry': mapping(done)
        })
'''
