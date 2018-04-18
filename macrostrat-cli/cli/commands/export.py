from .base import Base
import sys
from subprocess import call
import datetime
import os
from psycopg2.extensions import AsIs
import fiona
from shapely.wkb import loads
from shapely.geometry import MultiPolygon, mapping
cwd = os.getcwd()
from psycopg2.extras import RealDictCursor
import sqlite3


class Export(Base):
    '''
    macrostrat export <source_id or bbox>:
        Create a GeoPackage of a given map source or from a bounding box. If a
        source_id is provided, the following data will be dumped:
            + The original polygon data
            + The original line data
            + The homogenized polygon data
            + The homogenized line data
            + The record from maps.sources
        If a bounding box is provided, the following data will be dumped:
            + carto polygon table for appropriate scale
            + carto line table for appropriate scale
            + The necessary records from maps.sources
            + All homogenized polygon scales
            + All homogenized line scales

    Usage:
      macrostrat export <source_id or bbox>
      macrostrat export -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
      --force_scale                     Export the given scale with a bbox
    Examples:
      macrostrat export 123
      macrostrat export -90 43 -90 45
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    '''
    crs = {
        'no_defs': True,
        'ellps': 'WGS84',
        'datum': 'WGS84',
        'proj': 'longlat'
    }
    maps_schema = {
        'map_id': 'int',
        'orig_id': 'int',
        'source_id': 'int',
        'name': 'str',
        'strat_name': 'str',
        'age': 'str',
        'lith': 'str',
        'descrip': 'str',
        'comments': 'str',
        'macro_t_int': 'str',
        'macro_b_int': 'str',
        'best_t_age': 'float',
        'best_b_age': 'float',
        'color': 'str'
    }

    lines_schema = {
        'line_id': 'int',
        'orig_id': 'int',
        'source_id': 'int',
        'name': 'str',
        'type': 'str',
        'direction': 'str',
        'descrip': 'str',
        'new_type': 'str',
        'new_direction': 'str'
    }

    maps_select = """
        SELECT
            m.map_id,
            m.orig_id,
            m.source_id,
            m.name,
            m.strat_name,
            m.age,
            m.lith,
            m.descrip,
            m.comments,
            ti.interval_name AS macro_t_int,
            tb.interval_name AS macro_b_int,
            l.best_age_top AS best_t_age,
            l.best_age_bottom AS best_b_age,
            l.color,
            m.geom
        FROM maps.%s m
        LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id
        LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id
        JOIN lookup_%s l ON m.map_id = l.map_id
        WHERE m.source_id = %s
    """

    maps_select_intersect = """
        SELECT
            m.map_id,
            m.orig_id,
            m.source_id,
            m.name,
            m.strat_name,
            m.age,
            m.lith,
            m.descrip,
            m.comments,
            ti.interval_name AS macro_t_int,
            tb.interval_name AS macro_b_int,
            l.best_age_top AS best_t_age,
            l.best_age_bottom AS best_b_age,
            l.color,
            ST_CollectionExtract(ST_Intersection(m.geom, %s), 3) AS geom
        FROM maps.%s m
        LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id
        LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id
        JOIN lookup_%s l ON m.map_id = l.map_id
        WHERE ST_Intersects(geom, %s)
    """

    lines_select = """
        SELECT
            line_id,
            orig_id,
            source_id,
            name,
            type,
            direction,
            descrip,
            new_type,
            new_direction,
            geom
        FROM lines.%s
        WHERE source_id = %s
    """

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)
        # Using the DictCursor instead of the NamedTuple cursor allows us to more easily
        # write dynamic schemas to the geopackage output
        self.pg['cursor'] = self.pg['connection'].cursor( cursor_factory=RealDictCursor )

    def write_sources(self, filename, sources):
        connection = sqlite3.connect('%s.gpkg' % filename)
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE sources (
                source_id integer PRIMARY KEY AUTOINCREMENT,
                name text,
                url text,
                ref_title text,
                authors text,
                ref_year text,
                ref_source text,
                isbn_doi text,
                scale text,
                license text
            )
        """)

        self.pg['cursor'].execute("""
            SELECT
                source_id,
                name,
                url,
                ref_title,
                authors,
                ref_year,
                ref_source,
                isbn_doi,
                scale,
                licence AS license
            FROM maps.sources
            WHERE source_id = ANY(%(source_ids)s)
        """, { 'source_ids': sources })
        for row in self.pg['cursor']:
            cursor.execute("""
                INSERT INTO sources
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [ row['source_id'], row['name'], row['url'], row['ref_title'], row['authors'], row['ref_year'], row['ref_source'], row['isbn_doi'], row['scale'], row['license'] ])

        connection.commit()
        connection.close()


    def get_table_schema(self, pg_schema, table):
        # First get the field names in the primary table
        self.pg['cursor'].execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %(primary_table)s AND table_schema = %(pg_schema)s
        """, { 'primary_table': table, 'pg_schema': pg_schema })
        columns = self.pg['cursor'].fetchall()

        # Format is { field_name: 'datatype' }
        table_schema = {}
        for col in columns:
            if col['column_name'] != 'geom':
                data_type = ''
                if col['data_type'] in ['integer', 'bigint', 'smallint']:
                    data_type = 'int'
                elif col['data_type'] in ['character varying', 'text', 'char']:
                    data_type = 'str'
                elif col['data_type'] == 'timestamp with time zone':
                    data_type = 'datetime'
                elif col['data_type'] == 'date':
                    data_type = 'date'
                elif col['data_type'] == 'boolean':
                    data_type = 'bool'
                elif col['data_type'] in ['double precision', 'numeric', 'real']:
                    data_type = 'float'
                else:
                    data_type = 'str'

                table_schema[col['column_name']] = data_type

        # Get a list of column names
        column_names = [ col['column_name'] for col in columns ]

        select = 'SELECT %s FROM %s.%s' % (','.join(column_names), pg_schema, table)

        return table_schema, select


    # Given a table, write a layer to a given geopackage
    def write_layer(self, filename, layer_name, geometry_type, select, select_params, table_schema):
        # Open the GeoPackage for writing
        with fiona.open(
            '%s.gpkg' % filename,
            'w',
            layer=layer_name,
            driver='GPKG',
            crs=Export.crs,
            schema={
                'geometry': geometry_type,
                'properties': table_schema
            }
        ) as output:
            self.pg['cursor'].execute(select, select_params)

            for row in self.pg['cursor']:
                # Create a shapely geometry from the wkb and dump it into a dict
                geometry =  mapping(loads(row['geom'], hex=True))
                del row['geom']
                # Make sure data types are correct
                for key in row:
                    # Postgres often returns these as decimals
                    if table_schema[key] == 'float':
                        row[key] = float(row[key])
                    elif table_schema[key] == 'str':
                        row[key] = str(row[key])
                # Write the row to the GeoPackage
                output.write({
                    'geometry': geometry,
                    'properties': row
                })

    def run(self):
        if len(self.args) == 1 or self.args[1] == '--help' or self.args[1] == '-h':
            print Export.__doc__
            sys.exit()

        # source_id mode
        if len(self.args) == 2:
            source_id = self.args[1]
            # Validate source_id
            self.pg['cursor'].execute("""
                SELECT name, scale, primary_table, primary_line_table
                FROM maps.sources
                WHERE source_id = %(source_id)s
            """, { 'source_id': source_id })
            source_info = self.pg['cursor'].fetchone()
            if source_info is None:
                print 'Source ID %s was not found or is invalid' % (source_id, )
                sys.exit()

            filename = source_info['name'].replace(' ', '_').replace(',', '').replace('1:', '').lower()

            # Write orignal units
            layer_schema, select = Export.get_table_schema(self, 'sources', source_info['primary_table'])
            Export.write_layer(self, filename, 'original_units', 'MultiPolygon', select, {}, layer_schema)

            # Write original lines
            layer_schema, select = Export.get_table_schema(self, 'sources', source_info['primary_line_table'])
            Export.write_layer(self, filename, 'original_lines', 'MultiLineString', select, {}, layer_schema)

            # Write homogenized units
            select = Export.maps_select % (source_info['scale'], source_info['scale'], source_id, )
            Export.write_layer(self, filename, 'units', 'MultiPolygon', select, {}, Export.maps_schema)

            # Write homogenized lines
            select = Export.lines_select % (source_info['scale'], source_id, )
            Export.write_layer(self, filename, 'lines', 'MultiLineString', select, {}, Export.lines_schema)

            # Write the metadata
            Export.write_sources(self, filename, [ int(source_id) ])

            print '     Wrote source_id %s to %s.gpkg' % (source_id, filename, )

        # bbox mode
        elif len(self.args) == 5:
            # Validate vertices
            try:
                xmin, ymin, xmax, ymax = [ float(l) for l in self.args[1:] ]
            except:
                print 'Invalid bounding box provided. Please make sure all vertices are numbers'
                sys.exit(1)

            if xmin > xmax or ymin > ymax:
                print 'Invalid bounding box. Please make sure it is in the format xmin ymin xmax ymax'
                sys.exit(1)

            # Get appropriate scale for carto purposes
            self.pg['cursor'].execute("""
                SELECT ST_Area(ST_MakeEnvelope(%(xmin)s, %(ymin)s, %(xmax)s, %(ymax)s)::geography)/1000000 as area
            """, { 'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax })
            area = int(self.pg['cursor'].fetchone()['area'])
            scale = 'large'
            # if area < 1000000:
            #     scale = 'large'
            # elif area < 15000000:
            #     scale = 'medium'
            # elif area < 80000000:
            #     scale = 'small'
            # else:
            #     scale = 'tiny'

            filename = '%s-%s-%s-%s' % (xmin, ymin, xmax, ymax)
            # Write carto units
            select = '''
                SELECT c.map_id, l.legend_id, l.source_id, name,
                strat_name,
                age,
                lith,
                descrip,
                comments,
                b_interval,
                t_interval,
                best_age_bottom,
                best_age_top,
                color,
                COALESCE(array_to_string(unit_ids, '|'), '') AS unit_ids,
                COALESCE(array_to_string(strat_name_ids, '|'), '') AS strat_name_ids,
                COALESCE(array_to_string(concept_ids, '|'), '') AS concept_ids,
                COALESCE(array_to_string(lith_ids, '|'), '') AS lith_ids,
                ST_Multi(geom) AS geom
                FROM carto_new.%s c
                JOIN maps.map_legend ON map_legend.map_id = c.map_id
                JOIN maps.legend l ON l.legend_id = map_legend.legend_id
                WHERE ST_Intersects(c.geom, %s)
            ''' % (scale, 'ST_SetSRID(ST_MakeEnvelope(%s, %s, %s, %s), 4326)' % (xmin, ymin, xmax, ymax), )

            Export.write_layer(self, filename, 'units', 'MultiPolygon', select, {}, {
                'map_id': 'int',
                'legend_id': 'int',
                'source_id': 'int',
                'name': 'str',
                'strat_name': 'str',
                'age': 'str',
                'lith': 'str',
                'descrip': 'str',
                'comments': 'str',
                'b_interval': 'int',
                't_interval': 'int',
                'best_age_bottom': 'str',
                'best_age_top': 'str',
                'color': 'str',
                'unit_ids': 'str',
                'strat_name_ids': 'str',
                'concept_ids': 'str',
                'lith_ids': 'str'
            })

            # Write carto lines
            select = '''
                SELECT c.line_id, ll.source_id, ll.name, ll.type, ll.direction, ll.descrip, ll.new_type, ll.new_direction, ST_Multi(c.geom) AS geom
                FROM carto_new.lines_%s c
                JOIN (
                    SELECT * FROM lines.tiny
                    UNION ALL
                    SELECT * FROM lines.small
                    UNION ALL
                    SELECT * FROM lines.medium
                    UNION ALL
                    SELECT * FROM lines.large
                ) ll ON c.line_id = ll.line_id
                WHERE ST_Intersects(c.geom, %s)
            ''' % (scale, 'ST_SetSRID(ST_MakeEnvelope(%s, %s, %s, %s), 4326)' % (xmin, ymin, xmax, ymax), )

            Export.write_layer(self, filename, 'lines', 'MultiLineString', select, {}, {
                'line_id': 'int',
                'source_id': 'int',
                'name': 'str',
                'type': 'str',
                'direction': 'str',
                'descrip': 'str',
                'new_type': 'str',
                'new_direction': 'str'
            })

            # Write legend
            connection = sqlite3.connect('%s.gpkg' % filename)
            connection.text_factory = str
            cursor = connection.cursor()

            # Write sources
            cursor.execute("""
                CREATE TABLE sources (
                    source_id integer PRIMARY KEY AUTOINCREMENT,
                    name text,
                    url text,
                    ref_title text,
                    authors text,
                    ref_year text,
                    ref_source text,
                    isbn_doi text,
                    scale text,
                    license text
                )
            """)

            select = '''
                SELECT
                    source_id,
                    name,
                    url,
                    ref_title,
                    authors,
                    ref_year,
                    ref_source,
                    isbn_doi,
                    scale,
                    licence AS license
                FROM maps.sources
                WHERE source_id IN (
                    SELECT DISTINCT ll.source_id
                    FROM (
                        SELECT * FROM lines.tiny
                        UNION ALL
                        SELECT * FROM lines.small
                        UNION ALL
                        SELECT * FROM lines.medium
                        UNION ALL
                        SELECT * FROM lines.large
                    ) ll
                    WHERE ST_Intersects(ll.geom, %s)
                )
            ''' % ('ST_SetSRID(ST_MakeEnvelope(%s, %s, %s, %s), 4326)' % (xmin, ymin, xmax, ymax), )
            self.pg['cursor'].execute(select)
            for row in self.pg['cursor']:
                cursor.execute("""
                    INSERT INTO sources
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [ row['source_id'], row['name'], row['url'], row['ref_title'], row['authors'], row['ref_year'], row['ref_source'], row['isbn_doi'], row['scale'], row['license'] ])

            connection.commit()
            connection.close()

            # Write the metadata

        else:
            print 'Invalid args. Please run macrostrat export --help to see available options'
            sys.exit(1)
