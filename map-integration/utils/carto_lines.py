import sys, os, time
from subprocess import call
import argparse
import psycopg2
from psycopg2.extensions import AsIs

sys.path = [os.path.join(os.path.dirname(__file__), os.pardir)] + sys.path
import credentials

parser = argparse.ArgumentParser(
    description="Create a carto table for a given scale",
    epilog="Example usage: python carto.py small")

parser.add_argument(nargs="?", dest="the_scale",
    default="0", type=str,
    help="The scale to generate a carto table for")

arguments = parser.parse_args()

# For a given scale, define which scales go into the carto table (ordered from 'bottom' to 'top' if you think of them as stacked)
layerOrder = {
    "tiny": ["tiny"],
    "small": ["tiny", "small"],
    "medium": ["small", "medium"],
    "large": ["medium", "large"]
}

if arguments.the_scale not in layerOrder:
    print 'Please enter a valid scale', [scale for scale in layerOrder]
    sys.exit(1)

if __name__ == '__main__':
    start = time.time()
    connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
    cursor = connection.cursor()

    if arguments.the_scale == 'tiny':
        sql = """
            CREATE TABLE carto.lines_tiny_new AS
            WITH l1 AS (
              SELECT a.line_id, a.geom,
                  'tiny'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.tiny a
              JOIN maps.sources b
              ON a.source_id = b.source_id
              WHERE priority = True
            ),l2 AS (
              SELECT a.line_id, a.geom,
                  'tiny'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.tiny a
              JOIN maps.sources b
                ON a.source_id = b.source_id
              LEFT JOIN l1 ON ST_Intersects(a.geom, l1.geom)
              WHERE priority = False
              AND l1.line_id IS NULL
              UNION
              SELECT * FROM l1
            )
            SELECT * FROM l2;

            CREATE INDEX ON carto.lines_tiny_new (line_id);
            CREATE INDEX ON carto.lines_tiny_new USING GiST (geom);

            ALTER TABLE carto.lines_tiny RENAME TO lines_tiny_old;
            ALTER TABLE carto.lines_tiny_new RENAME TO lines_tiny;
            DROP TABLE carto.lines_tiny_old;
        """
        cursor.execute(sql)
        connection.commit()

    else:
        sql = """
            CREATE TABLE carto.lines_%(target)s_new AS
            WITH l1 AS (
              SELECT line_id, geom,
                  '%(target)s'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.%(target)s a
              JOIN maps.sources b
              ON a.source_id = b.source_id
              WHERE priority = True
            ),l2 AS (
              SELECT a.line_id, a.geom,
                  '%(target)s'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.%(target)s a
              JOIN maps.sources b
                ON a.source_id = b.source_id
              LEFT JOIN l1 ON ST_Intersects(a.geom, l1.geom)
              WHERE priority = False
              AND l1.line_id IS NULL
              UNION
              SELECT * FROM l1
            ), l3 AS (
              SELECT a.line_id, a.geom,
                  '%(below)s'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.%(below)s a
              JOIN maps.sources b
                ON a.source_id = b.source_id
              LEFT JOIN l2 ON ST_Intersects(a.geom, l2.geom)
              WHERE priority = True
              AND l2.line_id IS NULL
              UNION
              SELECT * FROM l2
            ), l4 AS (
              SELECT a.line_id, a.geom,
                  '%(below)s'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.%(below)s a
              JOIN maps.sources b
                ON a.source_id = b.source_id
              LEFT JOIN l3 ON ST_Intersects(a.geom, l3.geom)
              WHERE priority = FALSE
              AND l3.line_id IS NULL
              UNION
              SELECT * FROM l3
            )
            SELECT * FROM l4;

            CREATE INDEX ON carto.lines_%(target)s_new (line_id);
            CREATE INDEX ON carto.lines_%(target)s_new USING GiST (geom);

            ALTER TABLE carto.lines_%(target)s RENAME TO lines_%(target)s_old;
            ALTER TABLE carto.lines_%(target)s_new RENAME TO lines_%(target)s;
            DROP TABLE carto.lines_%(target)s_old;
        """
        cursor.execute(sql, {
            "target": AsIs(arguments.the_scale),
            "below": AsIs(layerOrder[arguments.the_scale][1])
        })
        connection.commit()
    end = time.time()
    print 'Created carto.%s in ' % arguments.the_scale, int(end - start), 's'
