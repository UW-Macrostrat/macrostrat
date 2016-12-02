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
          SELECT line_id,
              ST_Intersection(a.geom, (
                SELECT ST_Envelope(rgeom)
                FROM maps.sources
                WHERE source_id = %(source_id)s
              )) as geom,
              '%(target)s'::text AS scale,
              a.source_id,
              COALESCE(a.name, '') AS name,
              COALESCE(a.new_type, '') AS type,
              COALESCE(a.direction, '') AS direction,
              COALESCE(a.descrip, '') AS descrip
          FROM lines.%(target)s a
          JOIN maps.sources b
          ON a.source_id = b.source_id
          JOIN (
             SELECT ST_Envelope(rgeom) as geom
             FROM maps.sources
             WHERE source_id = %(source_id)s
          ) c ON ST_Intersects(a.geom, c.geom)
          WHERE priority IS True;


        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
          SELECT a.line_id,
              ST_Difference(a.geom, (
                SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                FROM maps.sources x
                JOIN (
                   SELECT ST_Envelope(rgeom) as geom
                   FROM maps.sources
                   WHERE source_id = %(source_id)s
                ) w ON ST_Intersects(x.rgeom, w.geom)
                WHERE priority IS True and scale = '%(target)s'::text
              )) as geom,
              '%(target)s'::text AS scale,
              a.source_id,
              COALESCE(a.name, '') AS name,
              COALESCE(a.new_type, '') AS type,
              COALESCE(a.direction, '') AS direction,
              COALESCE(a.descrip, '') AS descrip
          FROM lines.%(target)s a
          JOIN maps.sources b ON a.source_id = b.source_id
          JOIN (
            SELECT ST_Envelope(rgeom) as geom
             FROM maps.sources
             WHERE source_id = %(source_id)s
          ) c ON ST_Intersects(a.geom, c.geom)
          WHERE priority IS False;

        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
          SELECT a.line_id,
              ST_Difference(a.geom, (
                SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                FROM maps.sources x
                JOIN (
                 SELECT ST_Envelope(rgeom) as geom
                 FROM maps.sources
                 WHERE source_id = %(source_id)s
                ) w ON ST_Intersects(x.rgeom, w.geom)
                WHERE scale = '%(target)s'
              )) as geom,
              '%(below)s'::text AS scale,
              a.source_id,
              COALESCE(a.name, '') AS name,
              COALESCE(a.new_type, '') AS type,
              COALESCE(a.direction, '') AS direction,
              COALESCE(a.descrip, '') AS descrip
          FROM lines.%(below)s a
          JOIN maps.sources b ON a.source_id = b.source_id
          JOIN (
            SELECT ST_Envelope(rgeom) as geom
            FROM maps.sources
            WHERE source_id = %(source_id)s
          ) c ON ST_Intersects(a.geom, c.geom)
          WHERE priority IS True;

        INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
          SELECT a.line_id,
              ST_Difference(a.geom, (
                SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                FROM maps.sources x
                JOIN (
                 SELECT ST_Envelope(rgeom) as geom
                 FROM maps.sources
                 WHERE source_id = %(source_id)s
                ) w ON ST_Intersects(x.rgeom, w.geom)
                WHERE scale = '%(target)s' OR (scale = '%(below)s'::text AND priority is True)
              )) as geom,
              '%(below)s'::text AS scale,
              a.source_id,
              COALESCE(a.name, '') AS name,
              COALESCE(a.new_type, '') AS type,
              COALESCE(a.direction, '') AS direction,
              COALESCE(a.descrip, '') AS descrip
          FROM lines.%(below)s a
          JOIN maps.sources b ON a.source_id = b.source_id
          JOIN (
            SELECT ST_Envelope(rgeom) as geom
            FROM maps.sources
            WHERE source_id = %(source_id)s
          ) c ON ST_Intersects(a.geom, c.geom)
          WHERE priority IS False;
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
                  COALESCE(a.new_type, '') AS type,
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
                  COALESCE(a.new_type, '') AS type,
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
            -- All priorities of the target scale
            CREATE TABLE carto.lines_%(target)s_new AS
                SELECT line_id, 'tiny' AS scale, tiny.source_id, COALESCE(tiny.name, '') AS name, COALESCE(tiny.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.tiny
                JOIN maps.sources ON tiny.source_id = sources.source_id
                WHERE scale = '%(target)s'::text AND priority = True
                UNION
                SELECT line_id, 'small' AS scale, small.source_id, COALESCE(small.name, '') AS name, COALESCE(small.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.small
                JOIN maps.sources ON small.source_id = sources.source_id
                WHERE scale = '%(target)s'::text AND priority = True
                UNION
                SELECT line_id, 'medium' AS scale, medium.source_id, COALESCE(medium.name, '') AS name, COALESCE(medium.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.medium
                JOIN maps.sources ON medium.source_id = sources.source_id
                WHERE scale = '%(target)s'::text AND priority = True
                UNION
                SELECT line_id, 'large' AS scale, large.source_id, COALESCE(large.name, '') AS name, COALESCE(large.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.large
                JOIN maps.sources ON large.source_id = sources.source_id
                WHERE scale = '%(target)s'::text AND priority = True;

            -- All low priorities of the target scale and all priorities of display_scale = target scale
            INSERT INTO carto.lines_%(target)s_new (line_id, geom, scale, source_id, name, type, direction, descrip)

                    SELECT line_id, 'tiny' AS scale, tiny.source_id, COALESCE(tiny.name, '') AS name, COALESCE(tiny.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                      SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                      FROM maps.sources x
                      WHERE scale = '%(target)s'::text AND priority = True
                    )) as geom
                    FROM lines.tiny
                    JOIN maps.sources ON tiny.source_id = sources.source_id
                    WHERE
                        ( scale = '%(target)s'::text AND priority = False )
                        OR
                        ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                    UNION
                    SELECT line_id, 'small' AS scale, small.source_id, COALESCE(small.name, '') AS name, COALESCE(small.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                      SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                      FROM maps.sources x
                      WHERE scale = '%(target)s'::text AND priority = True
                    )) as geom
                    FROM lines.small
                    JOIN maps.sources ON small.source_id = sources.source_id
                    WHERE
                        ( scale = '%(target)s'::text AND priority = False )
                        OR
                        ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                    UNION
                    SELECT line_id, 'medium' AS scale, medium.source_id, COALESCE(medium.name, '') AS name, COALESCE(medium.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                      SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                      FROM maps.sources x
                      WHERE scale = '%(target)s'::text AND priority = True
                    )) as geom
                    FROM lines.medium
                    JOIN maps.sources ON medium.source_id = sources.source_id
                    WHERE
                        ( scale = '%(target)s'::text AND priority = False )
                        OR
                        ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                    UNION
                    SELECT line_id, 'large' AS scale, large.source_id, COALESCE(large.name, '') AS name, COALESCE(large.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                      SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                      FROM maps.sources x
                      WHERE scale = '%(target)s'::text AND priority = True
                    )) as geom
                    FROM lines.large
                    JOIN maps.sources ON large.source_id = sources.source_id
                    WHERE
                        ( scale = '%(target)s'::text AND priority = False )
                        OR
                        ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text );

            -- All high priorities of the scale below
            INSERT INTO carto.lines_%(target)s_new (line_id, geom, scale, source_id, name, type, direction, descrip)
                SELECT line_id, 'tiny' AS scale, tiny.source_id, COALESCE(tiny.name, '') AS name, COALESCE(tiny.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( scale = '%(target)s'::text AND priority = False )
                      OR
                      ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                )) as geom,
                FROM lines.tiny
                JOIN maps.sources ON tiny.source_id = sources.source_id
                WHERE scale = '%(below)s'::text AND priority = True
                UNION
                SELECT line_id, 'small' AS scale, small.source_id, COALESCE(small.name, '') AS name, COALESCE(small.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( scale = '%(target)s'::text AND priority = False )
                      OR
                      ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                )) as geom,
                FROM lines.small
                JOIN maps.sources ON small.source_id = sources.source_id
                WHERE scale = '%(below)s'::text AND priority = True
                UNION
                SELECT line_id, 'medium' AS scale, medium.source_id, COALESCE(medium.name, '') AS name, COALESCE(medium.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( scale = '%(target)s'::text AND priority = False )
                      OR
                      ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                )) as geom,
                FROM lines.medium
                JOIN maps.sources ON medium.source_id = sources.source_id
                WHERE scale = '%(below)s'::text AND priority = True
                UNION
                SELECT line_id, 'large' AS scale, large.source_id, COALESCE(large.name, '') AS name, COALESCE(large.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( scale = '%(target)s'::text AND priority = False )
                      OR
                      ( '%(target)s'::text = ANY(display_scales) AND scale != '%(target)s'::text )
                )) as geom,
                FROM lines.large
                JOIN maps.sources ON large.source_id = sources.source_id
                WHERE scale = '%(below)s'::text AND priority = True;

            -- All low priorities of the scale below
            INSERT INTO carto.lines_%(target)s_new (line_id, geom, scale, source_id, name, type, direction, descrip)
                SELECT line_id, 'tiny' AS scale, tiny.source_id, COALESCE(tiny.name, '') AS name, COALESCE(tiny.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( '%(target)s'::text = ANY(display_scales))
                      OR
                      ( scale = '%(below)s'::text AND priority = True )
                )) as geom,
                FROM lines.tiny
                JOIN maps.sources ON tiny.source_id = sources.source_id
                WHERE ( scale = '%(below)s'::text AND priority = False )
                    OR
                    ( '%(below)s'::text = ANY(display_scales) AND scale != '%(below)s'::text )
                UNION
                SELECT line_id, 'small' AS scale, small.source_id, COALESCE(small.name, '') AS name, COALESCE(small.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( '%(target)s'::text = ANY(display_scales))
                      OR
                      ( scale = '%(below)s'::text AND priority = True )
                )) as geom,
                FROM lines.small
                JOIN maps.sources ON small.source_id = sources.source_id
                WHERE ( scale = '%(below)s'::text AND priority = False )
                    OR
                    ( '%(below)s'::text = ANY(display_scales) AND scale != '%(below)s'::text )
                UNION
                SELECT line_id, 'medium' AS scale, medium.source_id, COALESCE(medium.name, '') AS name, COALESCE(medium.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( '%(target)s'::text = ANY(display_scales))
                      OR
                      ( scale = '%(below)s'::text AND priority = True )
                )) as geom,
                FROM lines.medium
                JOIN maps.sources ON medium.source_id = sources.source_id
                WHERE ( scale = '%(below)s'::text AND priority = False )
                    OR
                    ( '%(below)s'::text = ANY(display_scales) AND scale != '%(below)s'::text )
                UNION
                SELECT line_id, 'large' AS scale, large.source_id, COALESCE(large.name, '') AS name, COALESCE(large.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, ST_Difference(geom, (
                  SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                  FROM maps.sources x
                  WHERE
                      ( '%(target)s'::text = ANY(display_scales))
                      OR
                      ( scale = '%(below)s'::text AND priority = True )
                )) as geom,
                FROM lines.large
                JOIN maps.sources ON large.source_id = sources.source_id
                WHERE ( scale = '%(below)s'::text AND priority = False )
                    OR
                    ( '%(below)s'::text = ANY(display_scales) AND scale != '%(below)s'::text );



            INSERT INTO carto.lines_%(target)s (line_id, geom, scale, source_id, name, type, direction, descrip)
              SELECT a.line_id,
                  ST_Difference(a.geom, (
                    SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
                    FROM maps.sources x
                    WHERE scale = '%(target)s' OR (scale = '%(below)s'::text AND priority is True)
                  )) as geom,
                  '%(below)s'::text AS scale,
                  a.source_id,
                  COALESCE(a.name, '') AS name,
                  COALESCE(a.new_type, '') AS type,
                  COALESCE(a.direction, '') AS direction,
                  COALESCE(a.descrip, '') AS descrip
              FROM lines.%(below)s a
              JOIN maps.sources b ON a.source_id = b.source_id
              WHERE priority IS False;

              SELECT line_id,
                  geom,
                  scale,
                  source_id,
                  name,
                  type,
                  direction,
                  descrip
              FROM (
                SELECT line_id, 'tiny' AS scale, tiny.source_id, COALESCE(tiny.name, '') AS name, COALESCE(tiny.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.tiny
                JOIN maps.sources ON tiny.source_id = sources.source_id
                WHERE '%(target)s'::text = ANY(display_scales) AND priority = False
                UNION
                SELECT line_id, 'small' AS scale, small.source_id, COALESCE(small.name, '') AS name, COALESCE(small.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.small
                JOIN maps.sources ON small.source_id = sources.source_id
                WHERE '%(target)s'::text = ANY(display_scales) AND priority = False
                UNION
                SELECT line_id, 'medium' AS scale, medium.source_id, COALESCE(medium.name, '') AS name, COALESCE(medium.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.medium
                JOIN maps.sources ON medium.source_id = sources.source_id
                WHERE '%(target)s'::text = ANY(display_scales) AND priority = False
                UNION
                SELECT line_id, 'large' AS scale, large.source_id, COALESCE(large.name, '') AS name, COALESCE(large.new_type, '') AS type, COALESCE(direction, '') AS direction, COALESCE(descrip, '') AS descrip, geom
                FROM lines.large
                JOIN maps.sources ON large.source_id = sources.source_id
                WHERE '%(target)s'::text = ANY(display_scales) AND priority = False
              ) a;

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
    print 'Created carto.%s in %s s' % (arguments.the_scale, int(end - start))
