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

parser.add_argument("-s", "--source_id", dest="source_id",
  default="", type=str, required=False,
  help="The source_id that should be added to the carto_lines tables")

arguments = parser.parse_args()

# For a given scale, define which scales go into the carto table (ordered from 'bottom' to 'top' if you think of them as stacked)
layerOrder = {
    "tiny": ["tiny"],
    "small": ["tiny", "small"],
    "medium": ["small", "medium"],
    "large": ["medium", "large"]
}

scaleIsIn = {
    "tiny": ["tiny"],
    "small": ["small", "medium"],
    "medium": ["medium", "large"],
    "large": ["large"]
}

if arguments.the_scale not in layerOrder and len(arguments.source_id) == 0:
    print 'Please enter a valid scale', [scale for scale in layerOrder]
    sys.exit(1)

def refresh(scale, source_id):
    sql = """
        DELETE FROM carto.lines_%(target)s WHERE ST_Intersects(
                geom,
                (SELECT ST_Envelope(rgeom)
                 FROM maps.sources
                 WHERE source_id = %(source_id)s )
        );

        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
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
            AND ST_Intersects(
                    geom,
                    (SELECT ST_Envelope(rgeom)
                     FROM maps.sources
                     WHERE source_id = %(source_id)s )
            );

        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
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
          LEFT JOIN carto.lines_%(target)s c ON ST_Intersects(a.geom, c.geom)
          WHERE priority = False
          AND c.line_id IS NULL
          AND ST_Intersects(
                a.geom,
                (SELECT ST_Envelope(rgeom)
                FROM maps.sources
                WHERE source_id = %(source_id)s )
          );

        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
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
          LEFT JOIN (
            SELECT source_id, rgeom
            FROM maps.sources
            WHERE scales = '%(target)s'
          ) c ON ST_Intersects(a.geom, c.geom)
        --  LEFT JOIN carto.lines_%(target)s c ON ST_Intersects(a.geom, c.geom)
          WHERE priority = True
          AND c.source_id IS NULL
          AND ST_Intersects(
                a.geom,
                (SELECT ST_Envelope(rgeom)
                FROM maps.sources
                WHERE source_id = %(source_id)s )
          );

        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
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
          LEFT JOIN (
            SELECT source_id, rgeom
            FROM maps.sources
            WHERE scales = '%(target)s'
          ) c ON ST_Intersects(a.geom, c.geom)
         -- LEFT JOIN carto.lines_%(target)s c ON ST_Intersects(a.geom, c.geom)
          WHERE priority = FALSE
          AND c.source_id IS NULL
          AND ST_Intersects(
                a.geom,
                (SELECT ST_Envelope(rgeom)
                FROM maps.sources
                WHERE source_id = %(source_id)s )
          );
    """
    cursor.execute(sql, {
        "target": AsIs(scale),
        "below": AsIs(layerOrder[scale][0]),
        "source_id": source_id
    })
    connection.commit()

if __name__ == '__main__':
    start = time.time()
    connection = psycopg2.connect(dbname="burwell", user=credentials.pg_user, host=credentials.pg_host, port=credentials.pg_port)
    cursor = connection.cursor()

    if len(arguments.source_id):
        # Get scale of source_id
        cursor.execute("SELECT scale FROM maps.sources WHERE source_id = %(source_id)s", { "source_id": arguments.source_id })
        scale = cursor.fetchone()[0]
        for each in scaleIsIn[scale]:
            refresh(each, arguments.source_id)


    elif arguments.the_scale == 'tiny':
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
              WHERE priority = True;

            INSERT INTO carto.lines_%(target)s_new (line_id, geom, scale, source_id, name, type, direction, descrip)
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
              LEFT JOIN carto.lines_%(target)s_new c ON ST_Intersects(a.geom, c.geom)
              WHERE priority = False
              AND c.line_id IS NULL;

            INSERT INTO carto.lines_%(target)s_new (line_id, geom, scale, source_id, name, type, direction, descrip)
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
              LEFT JOIN carto.lines_%(target)s_new c ON ST_Intersects(a.geom, c.geom)
              WHERE priority = True
              AND c.line_id IS NULL;

            INSERT INTO carto.lines_%(target)s_new (line_id, geom, scale, source_id, name, type, direction, descrip)
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
              LEFT JOIN carto.lines_%(target)s_new c ON ST_Intersects(a.geom, c.geom)
              WHERE priority = FALSE
              AND c.line_id IS NULL;

            CREATE INDEX ON carto.lines_%(target)s_new (line_id);
            CREATE INDEX ON carto.lines_%(target)s_new USING GiST (geom);

            ALTER TABLE carto.lines_%(target)s RENAME TO lines_%(target)s_old;
            ALTER TABLE carto.lines_%(target)s_new RENAME TO lines_%(target)s;
            DROP TABLE carto.lines_%(target)s_old;
        """
        cursor.execute(sql, {
            "target": AsIs(arguments.the_scale),
            "below": AsIs(layerOrder[arguments.the_scale][0])
        })
        connection.commit()
    end = time.time()
    print 'Created carto.%s in ' % arguments.the_scale, int(end - start), 's'
