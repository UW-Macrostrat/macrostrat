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

scales = ["tiny", "small", "medium", "large"]

if arguments.the_scale not in layerOrder and len(arguments.source_id) == 0:
    print 'Please enter a valid scale', [scale for scale in layerOrder]
    sys.exit(1)

def piece(scale, geom_query, where):
    return """
    SELECT
        line_id,
        '%(scale)s' AS scale,
        x.source_id,
        COALESCE(x.name, '') AS name,
        COALESCE(x.new_type, '') AS type,
        COALESCE(direction, '') AS direction,
        COALESCE(descrip, '') AS descrip,
        %(geom_query)s
    FROM lines.%(scale)s x
    JOIN maps.sources ON x.source_id = sources.source_id
    WHERE %(where)s
    """ % {
     "scale": scale,
     "geom_query": geom_query,
     "where": where
    }

def geom_chop(where):
     return """ ST_Difference(geom, (
      SELECT COALESCE(ST_Union(rgeom), 'POLYGON EMPTY')
          FROM maps.sources x
          WHERE %(where)s
      )) as geom""" % { "where": where }


def piece_refresh(scale, geom_query, where, source_id):
    return """
    SELECT
        line_id,
        '%(scale)s' AS scale,
        a.source_id,
        COALESCE(a.name, '') AS name,
        COALESCE(a.new_type, '') AS type,
        COALESCE(direction, '') AS direction,
        COALESCE(descrip, '') AS descrip,
        %(geom_query)s
    FROM lines.%(scale)s a
    JOIN maps.sources ON a.source_id = sources.source_id
    JOIN (
      SELECT rgeom
       FROM maps.sources
       WHERE source_id = %(source_id)s
    ) c ON ST_Intersects(a.geom, c.rgeom)
    WHERE %(where)s
    """ % {
     "scale": scale,
     "geom_query": geom_query,
     "where": where,
     "source_id": source_id
    }

def geom_chop_refresh(where, source_id):
     return """ ST_Difference(a.geom, (
          SELECT COALESCE(ST_Union(x.rgeom), 'POLYGON EMPTY')
          FROM maps.sources x
          JOIN (
           SELECT rgeom
           FROM maps.sources
           WHERE source_id = %(source_id)s
          ) w ON ST_Intersects(x.rgeom, w.rgeom)
          WHERE %(where)s
      )) as geom""" % { "where": where, "source_id": source_id }


def refresh(scale, source_id):
    target = AsIs(scale)
    below = AsIs(layerOrder[scale][0])

    insert = "INSERT INTO carto.lines_%(target)s (line_id, scale, source_id, name, type, direction, descrip, geom) " % {"target": target}

    # from top to bottom:
    filter_types = ["scale = '%(target)s'::text AND priority = True"  % {"target": target},
     "scale = '%(target)s'::text AND priority = False"  % {"target": target},
     "'%(target)s'::text = ANY(display_scales) AND priority = True AND scale != '%(target)s'::text"  % {"target": target},
     "'%(target)s'::text = ANY(display_scales) AND priority = False AND scale != '%(target)s'::text" % {"target": target},
     "scale = '%(below)s'::text AND priority = True" % {"below": below},
     "scale = '%(below)s'::text AND priority = False" % {"below": below},
     "'%(below)s'::text = ANY(display_scales) AND priority = True AND scale != '%(below)s'::text" % {"below": below},
     "'%(below)s'::text = ANY(display_scales) AND priority = False AND scale != '%(below)s'::text" % {"below": below}]

    # Chop out a footprint = the target source's rgeom
    sql = ["""
    UPDATE carto.lines_%(target)s
    SET geom = ST_Difference(geom, (
        SELECT rgeom
        FROM maps.sources
        WHERE source_id = %(source_id)s
    ));
    DELETE FROM carto.lines_%(target)s WHERE geometrytype(geom) NOT IN ('LINESTRING', 'MULTILINESTRING');
    """ % { "target": target, "source_id": source_id }]

    for idx, each in enumerate(filter_types):
        for scale in scales:
            if idx == 0:
                sql.append(insert + piece_refresh(scale, "a.geom", filter_types[idx], source_id) + ";")
            else:
                sql.append(insert + piece_refresh(scale, geom_chop_refresh(" OR ".join([ "(" + d + ")" for i, d in enumerate(filter_types) if i < idx ]), source_id), filter_types[idx], source_id) + ";")

    sql.append("DELETE FROM carto.lines_%(target)s WHERE geometrytype(geom) NOT IN ('LINESTRING', 'MULTILINESTRING');" % { "target": target })

    for idx, statement in enumerate(sql):
        print idx + 1, ' of ', len(sql)
        cursor.execute(statement)
        connection.commit()

    sys.exit()


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
        # 1. scale = target and priority = true
        # 2. scale = target and priority = false
        # 3. target in display_scale and priority = true and scale != target
        # 4. target in display_scale and priority = false and scale != target
        # 5. scale = below and priority = true
        # 6. scale = below and priority = false
        # 7. below in display_scale and priority = true and scale != below
        # 8. below in display_scale and priority = false and scale != below

        target = AsIs(arguments.the_scale)
        below = AsIs(layerOrder[arguments.the_scale][0])

        insert = "INSERT INTO carto.lines_%(target)s_new (line_id, scale, source_id, name, type, direction, descrip, geom) " % {"target": target}

        sql = ["""DROP TABLE IF EXISTS carto.lines_%(target)s_new; CREATE TABLE carto.lines_%(target)s_new (
            line_id integer,
            scale text,
            source_id integer,
            name text,
            type text,
            direction text,
            descrip text,
            geom geometry
        );""" % {"target": target}]

        # from top to bottom:
        filter_types = ["scale = '%(target)s'::text AND priority = True"  % {"target": target},
         "scale = '%(target)s'::text AND priority = False"  % {"target": target},
         "'%(target)s'::text = ANY(display_scales) AND priority = True AND scale != '%(target)s'::text"  % {"target": target},
         "'%(target)s'::text = ANY(display_scales) AND priority = False AND scale != '%(target)s'::text" % {"target": target},
         "scale = '%(below)s'::text AND priority = True" % {"below": below},
         "scale = '%(below)s'::text AND priority = False" % {"below": below},
         "'%(below)s'::text = ANY(display_scales) AND priority = True AND scale != '%(below)s'::text" % {"below": below},
         "'%(below)s'::text = ANY(display_scales) AND priority = False AND scale != '%(below)s'::text" % {"below": below}]


        for idx, each in enumerate(filter_types):
            for scale in scales:
                if idx == 0:
                    sql.append(insert + piece(scale, "geom", filter_types[idx]) + ";")
                else:
                    sql.append(insert + piece(scale, geom_chop(" OR ".join([ "(" + d + ")" for i, d in enumerate(filter_types) if i < idx ])), filter_types[idx]) + ";")

        for idx, statement in enumerate(sql):
            print idx + 1, ' of ', len(sql)
            cursor.execute(statement)
            connection.commit()

        cursor.execute("""
            DELETE FROM carto.lines_%(target)s_new WHERE geometrytype(geom) NOT IN ('LINESTRING', 'MULTILINESTRING');
            CREATE INDEX ON carto.lines_%(target)s_new (line_id);
            CREATE INDEX ON carto.lines_%(target)s_new USING GiST (geom);
            ALTER TABLE carto.lines_%(target)s RENAME TO lines_%(target)s_old;
            ALTER TABLE carto.lines_%(target)s_new RENAME TO lines_%(target)s;
            DROP TABLE carto.lines_%(target)s_old;
        """, {
            "target": target
        })
        connection.commit()
        sys.exit()


    end = time.time()
    print 'Created carto.%s in %s s' % (arguments.the_scale, int(end - start))
