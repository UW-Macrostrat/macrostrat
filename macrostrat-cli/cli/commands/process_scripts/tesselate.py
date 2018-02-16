import sys
from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor
import numpy as np
from scipy.spatial import Voronoi
from shapely.ops import cascaded_union
from shapely.geometry import Polygon, Point, MultiPoint, mapping, shape
import shapely.ops as ops
from shapely.wkt import loads
import pyproj
from functools import partial
import json
import re
from .. import schlep
from ..base import Base
import urllib2

class Tesselate(Base):
    '''
    macrostrat process tesselate
        Given some Macrostrat column centroids, create polygon geometries

    Parameters
        One of the following is required:
            --col_id - (int/int[]) one or many comma-delimited column ids
            --col_group_id - (int/int[]) one or many comma-delimited col_group_ids
            --project_id - (int/int[]) one or many comma-delimited project_ids

        Options:
            --boundary_id - (int) a boundary_id from geologic_boundaries.boundaries
                to use to cut the tesselated polygons
            --boundary_polygon - (text) a valid WKT polygon to use to cut the
                tesselated polygons
            --snap_to_nearest - (boolean) if only a single col_id is passed,
                create a polygon whose radius is equal to the distance to the
                nearest existing column centroid
            --buffer - (float) if only a single col_id is passed, create a polygon
                with the given radius. Good for things like Deep Sea columns
            --allow_overlap - (boolean) do not cut the resultant polygons by all
                other existing column polygons. Will result in overlapping geometries.

        *NB*: If multiple columns are passed and no options are provided, the
              tesselated polygons will be clipped by a polygon whose centroid is
              the center of all columns being operated on and whose radius is
              equivalent to the maximum distance between two columns being operated on.

    Examples:
      macrostrat process tesselate --col_id=1,2,3 --boundary_id=987
      macrostrat process tesselate --col_group_id=76 --boundary_id=345
      macrostrat process tesselate --col_id=54 --snap_to_nearest=True
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    '''

    meta = {
        'mariadb': True,
        'pg': True,
        'usage': """
            Adds a given source to the proper carto line tables.
        """,
        'required_args': {

        }
    }

    source_id = None
    pg = {
        'connection': None,
        'cursor': None
    }
    mariadb = {
        'connection': None,
        'cursor': None
    }

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def debug(self, tesselation, columns, clip_polygon):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": json.loads(json.dumps(mapping(f['polygon'])))} for f in tesselation
            ]
        }
        with open('tesselation.json', 'w') as out:
            json.dump(geojson, out)


        point_geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": { "type": "Point", "coordinates": [float(p['lng']), float(p['lat'])] }} for p in columns
            ]
        }
        with open('points.json', 'w') as out:
            json.dump(point_geojson, out)


        if clip_polygon is not None:
            clip_geojson = {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {}, "geometry": json.loads(json.dumps(mapping(clip_polygon)))}
                ]
            }

            with open('clip.json', 'w') as out:
                json.dump(clip_geojson, out)


    def voronoi_finite_polygons_2d(self, vor, radius=None):
        # via https://gist.github.com/pv/8036995 with minor mods

        if vor.points.shape[1] != 2:
            raise ValueError('Requires 2D input')

        new_regions = []
        new_vertices = vor.vertices.tolist()

        center = vor.points.mean(axis=0)
        if radius is None:
            radius = vor.points.ptp().max()

        # Construct a map containing all ridges for a given point
        all_ridges = {}
        for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
            all_ridges.setdefault(p1, []).append((p2, v1, v2))
            all_ridges.setdefault(p2, []).append((p1, v1, v2))

        # Reconstruct infinite regions
        for p1, region in enumerate(vor.point_region):
            vertices = vor.regions[region]

            if all(v >= 0 for v in vertices):
                # finite region
                new_regions.append(vertices)
                continue

            # reconstruct a non-finite region
            if p1 not in all_ridges:
                continue
            ridges = all_ridges[p1]
            new_region = [v for v in vertices if v >= 0]

            for p2, v1, v2 in ridges:
                if v2 < 0:
                    v1, v2 = v2, v1
                if v1 >= 0:
                    # finite ridge: already in the region
                    continue

                # Compute the missing endpoint of an infinite ridge

                t = vor.points[p2] - vor.points[p1] # tangent
                t /= np.linalg.norm(t)
                n = np.array([-t[1], t[0]])  # normal

                midpoint = vor.points[[p1, p2]].mean(axis=0)
                direction = np.sign(np.dot(midpoint - center, n)) * n
                far_point = vor.vertices[v2] + direction * radius

                new_region.append(len(new_vertices))
                new_vertices.append(far_point.tolist())

            # sort region counterclockwise
            vs = np.asarray([new_vertices[v] for v in new_region])
            c = vs.mean(axis=0)
            angles = np.arctan2(vs[:,1] - c[1], vs[:,0] - c[0])
            new_region = np.array(new_region)[np.argsort(angles)]

            # finish
            new_regions.append(new_region.tolist())

        return new_regions, np.asarray(new_vertices)

    def run(self, args):
        if '--help' in args or '-h' in args:
            print Tesselate.__doc__
            sys.exit()

        clip_polygon = None
        column_buffer = None
        parameters = {}
        for arg in args:
            arg = arg.decode('utf8')
            parts = arg.split('=')
            if len(parts) != 2:
                print 'Invalid argument - %s' % (arg, )
            clean_part = re.sub(r'-', '', re.sub(u'\u2014', '', parts[0]))
            parameters[clean_part] = parts[1].split(',')

        if len(parameters) < 1:
            print Tesselate.__doc__
            sys.exit(1)

        # Validate the parameters passed to the script
        column_params = [ 'col_id', 'col_group_id', 'project_id' ]
        clip_params = [ 'boundary_id', 'boundary_polygon', 'snap_to_nearest', 'buffer' ]
        optional_params = [ 'allow_overlap' ]

        if len(set(parameters.keys()).intersection(column_params)) == 0:
            print ' Please provide one of the following parameters to select columns:'
            for p in column_params:
                print '     -> %s' % (p, )
            sys.exit(1)

        if len(set(parameters.keys()).intersection(column_params)) > 1:
            print ' Only one column selection parameter can be provided. Please provide one of the following parameters to select columns:'
            for p in column_params:
                print '     -> %s' % (p, )
            sys.exit(1)

        # if len(set(parameters.keys()).intersection(clip_params)) == 0:
        #     print ' Please provide one of the following parameters to clip columns:'
        #     for p in clip_params:
        #         print '     -> %s' % (p, )
        #     sys.exit(1)

        if len(set(parameters.keys()).intersection(clip_params)) > 1:
            print ' Only one clip parameter can be provided. Please provide one of the following parameters to clip polygons:'
            for p in clip_params:
                print '     -> %s' % (p, )
            sys.exit(1)

        # Validate column_params
        column_param_key = list(set(parameters.keys()).intersection(column_params))[0]
        for val in parameters[column_param_key]:
            if not val.isdigit():
                print ' Value %s provided to parameter %s is invalid. It must be an integer' % (val, column_param_key, )

        # Validate snap_to_nearest
        if 'snap_to_nearest' in parameters:
            val = parameters['snap_to_nearest'][0].title()
            if val == 'True':
                val = True
            elif val == 'False':
                val = False
            else:
                print ' Invalid value for parameter `snap_to_nearest`. Must be either `True` or `False`'
                sys.exit(1)
            parameters['snap_to_nearest'] = val

            if 'boundary_id' in parameters:
                print ' You cannot pass %s or any other clip parameters when using `snap_to_nearest`' % ('boundary_id', )
                sys.exit(1)
            if 'boundary_polygon' in parameters:
                print ' You cannot pass %s or any other clip parameters when using `snap_to_nearest`' % ('boundary_polygon', )
                sys.exit(1)

        # Validate allow_overlap
        if 'allow_overlap' in parameters:
            val = parameters['allow_overlap'][0].title()
            if val == 'True':
                val = True
            elif val == 'False':
                val = False
            else:
                print ' Invalid value for parameter `allow_overlap`. Must be either `True` or `False`'
                sys.exit(1)
            parameters['allow_overlap'] = val

        # Validate the buffer parameter
        if 'buffer' in parameters:
            if 'boundary_id' in parameters:
                print ' You cannot pass %s or any other clip parameters when using `buffer`' % ('boundary_id', )
                sys.exit(1)
            if 'boundary_polygon' in parameters:
                print ' You cannot pass %s or any other clip parameters when using `buffer`' % ('boundary_polygon', )
                sys.exit(1)
            if 'snap_to_nearest' in parameters:
                print ' You cannot pass %s or any other clip parameters when using `buffer`' % ('snap_to_nearest', )
                sys.exit(1)

            try:
                parameters['buffer'] = float(parameters['buffer'])
            except:
                print ' %s is an invalid buffer parameter. Please pass a valid value' % (parameters['buffer'], )
                sys.exit(1)

            if parameters['buffer'] > 3 or parameters['buffer'] < 0:
                print ' The buffer value must be between 0 and 3. %s is invalid' % (parameters['buffer'], )
                sys.exit(1)

        # Validate the polygon
        if 'boundary_polygon' in parameters:
            boundary_polygon = loads(parameters['boundary_polygon'])
            if not boundary_polygon.is_valid:
                print ' Invalid boundary polygon'
                sys.exit(1)

        # Validate the boundary_id(s)
        if 'boundary_id' in parameters:
            for val in parameters['boundary_id']:
                if not val.isdigit():
                    print ' Value %s provided to parameter boundary_id is invalid. It must be an integer' % (val, )
            parameters['boundary_id'] = [ int(val) for val in parameters['boundary_id' ]]


        # Get the column coordinates
        sql_key = 'id' if column_param_key == 'col_id' else column_param_key
        sql_params = ','.join([ '%s' for val in parameters[column_param_key] ])
        self.mariadb['cursor'].execute("""
            SELECT id, lat, lng
            FROM cols
            WHERE """ + sql_key + """ IN (""" + sql_params + """)
        """, parameters[column_param_key])
        columns = self.mariadb['cursor'].fetchall()

        # Validate
        if column_param_key == 'id' and len(columns) != len(parameters[column_param_key]):
            found_columns = [ col['id'] for col in columns ]
            difference = set([ int(q) for q in parameters[column_param_key] ]).difference(found_columns)
            print ' The following columns were not found in the database:'
            for p in difference:
                print '     -> %s' % (p, )
            sys.exit(1)

        # TODO: Verify that something was fetched
        if len(columns) == 0:
            print ' No columns were found'
            sys.exit()


        # Get the clip polygon
        if 'boundary_id' in parameters:
            self.pg['cursor'].execute("""
                SELECT ST_AsGeoJSON((ST_dump(ST_Union(geom))).geom) AS geom
                FROM geologic_boundaries.boundaries
                WHERE boundary_id = ANY(%(boundary_id)s)
            """, { 'boundary_id': [ int(p) for p in parameters['boundary_id'] ] })
            clip_polygon = self.pg['cursor'].fetchone()

            # Verify that something was fetched
            if len(clip_polygon) == 0:
                print ' Invalid boundary polygon. Not found'
                sys.exit(1)

            clip_polygon = shape(json.loads(clip_polygon[0]))

        elif 'boundary_polygon' in parameters:
            clip_polygon = loads(parameters['boundary_polygon'])

        elif len(columns) > 1:
            # TODO: comment this A LOT
            distances = []
            for p1 in columns:
                p1 = Point([float(p1['lng']), float(p1['lat'])])
                for p2 in columns:
                    p2 = Point([float(p2['lng']), float(p2['lat'])])
                    distances.append(p1.distance(p2))
            max_distance = max(distances)
            all_points = MultiPoint([ (float(p['lng']), float(p['lat'])) for p in columns ])
            all_points_center = all_points.centroid
            clip_polygon = all_points_center.buffer(max_distance).envelope
            print clip_polygon

        # Validate that all columns are inside the clip polygon, if applicable
        if 'boundary_id' in parameters or 'boundary_polygon' in parameters:
            not_inside = []
            for p in columns:
                if not clip_polygon.contains(Point([float(p['lng']), float(p['lat'])])):
                    not_inside.append(p)

            if len(not_inside) > 0:
                print '  ERROR - the following columns are outside of the clipping polygon:'
                for point in not_inside:
                    print '     -> %s' % (point['id'])
                sys.exit(1)



        #
        # # Validate that all columns do not overlap with existing column geometries
        # inside_columns = []
        # for column in columns:
        #     if all_columns.contains(Point([float(p['lng']), float(p['lat'])])):
        #         inside_columns.append(column)
        #
        # if len(inside_columns) > 0:
        #     print '  ERROR - the following columns overlap the polygons of existing columns:'
        #     for point in inside_columns:
        #         print '     -> %s' % (point['id'])
        #     sys.exit(1)

        # Tesselation time
        if len(columns) == 1:
            if 'buffer' in parameters:
                unclipped_polygons = [ column.buffer(parameters['buffer']) for column in columns ]
            elif 'snap_to_nearest' in parameters:
                # Need to get buffer distance
                self.pg['cursor'].execute("""
                    SELECT ST_Distance(coordinate, %(point)s) AS distance
                    FROM macrostrat.cols
                    WHERE id != %(col_id)s
                    ORDER BY %(point)s <-> coordinate
                    LIMIT 1
                """, {
                    'point': 'POINT(%s %s)' % (columns[0]['lng'], columns[0]['lat']),
                    'col_id': columns[0]['id']
                })
                result = self.pg['cursor'].fetchone()
                unclipped_polygons = [ Point([float(p['lng']), float(p['lat'])]).buffer(result[0]).envelope for p in columns ]
            else:
                print 'When only one column is provided, a valid `buffer` or `snap_to_nearest` must also be provided'
                sys.exit(1)
        else:
            # Create the tesselation; initially open-ended and not clipped to the clipping polygon
            tesselation = Voronoi(np.array( [ [float(p['lng']), float(p['lat'])] for p in columns ] ))
            # We have to do this BS because scipy voronoi doesn't create edges for vertices outside of convex hull of all the points
            regions, new_points =  Tesselate.voronoi_finite_polygons_2d(self, tesselation)
            unclipped_polygons = [ Polygon(new_points[r]) for r in regions ]


        if clip_polygon is not None:
            clipped_polygons = [ poly.intersection(clip_polygon) for poly in unclipped_polygons ]
        else:
            clipped_polygons = unclipped_polygons

        if 'allow_overlap' in parameters and parameters['allow_overlap'] is True:
            pass
        else:
            # Fetch all column polygons
            self.pg['cursor'].execute("""
                SELECT ST_AsGeoJSON(ST_Union(poly_geom)) AS geom
                FROM macrostrat.cols
                WHERE NOT (""" + sql_key + """ = ANY(%(ids)s))
            """, { 'ids': [ int(p) for p in parameters[column_param_key] ]})
            all_columns = shape(json.loads(self.pg['cursor'].fetchone()[0]))
            clipped_polygons = [ poly.difference(all_columns) for poly in clipped_polygons ]

        # Assign a tesselated polygon to each column
        assigned_polygons = []
        for column in columns:
            for polygon in clipped_polygons:
                if polygon.contains(Point([float(column['lng']), float(column['lat'])])):
                    assigned_polygons.append({ 'col_id': column['id'], 'polygon': polygon })
                    continue

        if len(assigned_polygons) != len(columns):
            print 'Not all column points were assigned a tesselated polygon. See debug geojson files for help.'
            #Tesselate.debug(self, clipped_polygons, columns, clip_polygon)
            sys.exit(1)

        # Update the database
        for column in assigned_polygons:
            # First check if it already exists in `col_areas`
            self.mariadb['cursor'].execute("""
                SELECT col_id
                FROM col_areas
                WHERE col_id = %s
            """, column['col_id'])
            col_id = self.mariadb['cursor'].fetchone()
            # If it doesn't exist, insert
            if col_id is None or len(col_id) == 0:
                self.mariadb['cursor'].execute("""
                    INSERT INTO col_areas (col_id, col_area)
                    VALUES (%s, ST_GeomFromText(%s))
                """, [ column['col_id'], column['polygon'].wkt ])
                self.mariadb['connection'].commit()
            # Otherwise update
            else:
                self.mariadb['cursor'].execute("""
                    UPDATE col_areas
                    SET col_area =  ST_GeomFromText(%s)
                    WHERE col_id = %s
                """, [ column['polygon'].wkt, column['col_id'] ])
                self.mariadb['connection'].commit()

            column_aea = ops.transform(
                partial(
                    pyproj.transform,
                    pyproj.Proj(init='EPSG:4326'),
                    pyproj.Proj(
                        proj='aea',
                        lat1=column['polygon'].bounds[1],
                        lat2=column['polygon'].bounds[3])),
                column['polygon'])

            # Print the area in m^2
            area = column_aea.area / 1000000

            self.mariadb['cursor'].execute("""
                UPDATE cols
                SET col_area = %s
                WHERE id = %s
            """, [area, column['col_id']])
            self.mariadb['connection'].commit()

        # Close connections, otherwise you'll have a bad time https://dba.stackexchange.com/a/133047/38677
        self.pg['connection'].close()
        self.mariadb['connection'].close()

        # Update postgres
        schlep_instance = schlep({
            'pg': self.pg['raw_connection'],
            'mariadb': self.mariadb['raw_connection']
        }, [ None, ''])

        schlep_instance.move_table('col_areas')
        schlep_instance.move_table('cols')

        urllib2.urlopen('http://localhost:5000/api/v2/coluns/refresh-cache?cacheRefreshKey=%s' % (self.credentials['cacheRefreshKey'], )).read()
