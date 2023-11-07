import sys, os, time
from subprocess import call
import argparse
import psycopg2
from psycopg2.extensions import AsIs
import yaml
with open('../credentials.yml', 'r') as f:
    credentials = yaml.load(f)

parser = argparse.ArgumentParser(
    description="Create a carto table for a given source or scale",
    epilog="Example usage: python carto.py -s 123 --or-- python carto.py small")

parser.add_argument(nargs="?", dest="the_scale",
    default="0", type=str,
    help="The scale to generate a carto table for")

parser.add_argument("-s", "--source_id", dest="source_id",
  default="", type=str, required=False,
  help="The source_id that should be added to the carto tables")

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
        a.map_id,
        a.orig_id,
        a.source_id,
        '%(scale)s' AS scale,
        COALESCE(a.name, '') AS name,
        COALESCE(a.strat_name, '') AS strat_name,
        COALESCE(a.age, '') AS age,
        COALESCE(a.lith, '') AS lith,
        COALESCE(a.descrip, '') AS descrip,
        COALESCE(a.comments, '') AS comments,
        a.t_interval AS t_int_id,
        ta.interval_name AS t_int,
        l.best_age_top::numeric AS best_age_top,
        a.b_interval AS b_int_id,
        tb.interval_name AS b_int,
        l.best_age_bottom::numeric AS best_age_bottom,
        l.color,
        l.unit_ids,
        l.strat_name_ids,
        l.lith_ids,
        %(geom_query)s

    FROM maps.%(scale)s a
    LEFT JOIN macrostrat.intervals ta ON ta.id = a.t_interval
    LEFT JOIN macrostrat.intervals tb ON tb.id = a.b_interval
    LEFT JOIN %(lookup)s l ON a.map_id = l.map_id

    JOIN maps.sources ON a.source_id = sources.source_id
    WHERE %(where)s
    """ % {
     "scale": scale,
     "geom_query": geom_query,
     "where": where,
     "lookup": AsIs("lookup_" + scale)
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
        a.map_id,
        a.orig_id,
        a.source_id,
        '%(scale)s' AS scale,
        COALESCE(a.name, '') AS name,
        COALESCE(a.strat_name, '') AS strat_name,
        COALESCE(a.age, '') AS age,
        COALESCE(a.lith, '') AS lith,
        COALESCE(a.descrip, '') AS descrip,
        COALESCE(a.comments, '') AS comments,
        a.t_interval AS t_int_id,
        ta.interval_name AS t_int,
        l.best_age_top::numeric AS best_age_top,
        a.b_interval AS b_int_id,
        tb.interval_name AS b_int,
        l.best_age_bottom::numeric AS best_age_bottom,
        l.color,
        l.unit_ids,
        l.strat_name_ids,
        l.lith_ids,
        %(geom_query)s

    FROM maps.%(scale)s a
    LEFT JOIN macrostrat.intervals ta ON ta.id = a.t_interval
    LEFT JOIN macrostrat.intervals tb ON tb.id = a.b_interval
    LEFT JOIN %(lookup)s l ON a.map_id = l.map_id

    JOIN maps.sources ON a.source_id = sources.source_id
    JOIN maps.sources c ON ST_Intersects(a.geom, c.rgeom)
    WHERE (c.source_id = %(source_id)s) AND %(where)s
    """ % {
     "scale": scale,
     "geom_query": geom_query,
     "where": where,
     "source_id": source_id,
     "lookup": AsIs("lookup_" + scale)
    }

def geom_chop_refresh(where, source_id):
     return """ ST_Difference(a.geom, (
          SELECT COALESCE(ST_Union(x.rgeom), 'POLYGON EMPTY')
          FROM maps.sources x
          JOIN maps.source w ON ST_Intersects(x.rgeom, w.rgeom)
          WHERE (w.source_id = %(source_id)s) AND %(where)s
      )) as geom""" % { "where": where, "source_id": source_id }


def refresh(scale, source_id):
    target = AsIs(scale)
    below = AsIs(layerOrder[scale][0])

    insert = "INSERT INTO carto.%(target)s (map_id, scale, source_id, geom) " % {"target": target}

    # from top to bottom:
    filter_types = ["sources.scale = '%(target)s'::text AND sources.priority = True"  % {"target": target},
     "sources.scale = '%(target)s'::text AND sources.priority = False"  % {"target": target},
     "'%(target)s'::text = ANY(display_scales) AND sources.priority = True AND sources.scale != '%(target)s'::text"  % {"target": target},
     "'%(target)s'::text = ANY(display_scales) AND sources.priority = False AND sources.scale != '%(target)s'::text" % {"target": target},
     "sources.scale = '%(below)s'::text AND sources.priority = True" % {"below": below},
     "sources.scale = '%(below)s'::text AND sources.priority = False" % {"below": below},
     "'%(below)s'::text = ANY(display_scales) AND sources.priority = True AND sources.scale != '%(below)s'::text" % {"below": below},
     "'%(below)s'::text = ANY(display_scales) AND sources.priority = False AND sources.scale != '%(below)s'::text" % {"below": below}]

    # Chop out a footprint = the target source's rgeom
    sql = ["""
    DELETE FROM carto.%(target)s
    USING maps.sources
    WHERE ST_Contains(rgeom, geom) AND sources.source_id = %(source_id)s;

    UPDATE carto.%(target)s
    SET geom = ST_Difference(geom, rgeom)
    FROM maps.sources
    WHERE ST_Intersects(geom, rgeom) AND sources.source_id = %(source_id)s;

    DELETE FROM carto.%(target)s WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
    """ % { "target": target, "source_id": source_id }]

    for idx, each in enumerate(filter_types):
        for scale in scales:
            if idx == 0:
                sql.append(insert + piece_refresh(scale, "a.geom", filter_types[idx], source_id) + ";")
            else:

                sql.append(insert + piece_refresh(scale, geom_chop_refresh(" OR ".join([ "(" + d + ")" for i, d in enumerate(filter_types) if i < idx ]), source_id), filter_types[idx], source_id) + ";")

    # Clean up bad or empty geometries
    sql.append("DELETE FROM carto.%(target)s WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');" % { "target": target })

    for idx, statement in enumerate(sql):
        print idx + 1, ' of ', len(sql)
        cursor.execute(statement)
        connection.commit()

    sys.exit()


if __name__ == '__main__':
    start = time.time()
    connection = psycopg2.connect(dbname=credentials["pg_db"], user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
    cursor = connection.cursor()

    # If a source_id is passed, refresh only that area
    if len(arguments.source_id):
        # Get scale of source_id
        cursor.execute("SELECT scale FROM maps.sources WHERE source_id = %(source_id)s", { "source_id": arguments.source_id })
        scale = cursor.fetchone()[0]
        for each in scaleIsIn[scale]:
            refresh(each, arguments.source_id)



    elif arguments.the_scale == 'tiny':
        sql = """
            CREATE TABLE carto.tiny_new AS
            SELECT
              a.map_id,
              a.orig_id,
              a.source_id,
              'tiny'::text AS scale,
              COALESCE(a.name, '') AS name,
              COALESCE(a.strat_name, '') AS strat_name,
              COALESCE(a.age, '') AS age,
              COALESCE(a.lith, '') AS lith,
              COALESCE(a.descrip, '') AS descrip,
              COALESCE(a.comments, '') AS comments,
              a.t_interval AS t_int_id,
              ta.interval_name AS t_int,
              l.best_age_top::numeric AS best_age_top,
              a.b_interval AS b_int_id,
              tb.interval_name AS b_int,
              l.best_age_bottom::numeric AS best_age_bottom,
              l.color,
              l.unit_ids,
              l.strat_name_ids,
              l.lith_ids,
              ST_SetSRID(a.geom, 4326) AS geom
            FROM maps.tiny a
            LEFT JOIN macrostrat.intervals ta ON ta.id = a.t_interval
            LEFT JOIN macrostrat.intervals tb ON tb.id = a.b_interval
            LEFT JOIN lookup_tiny l ON a.map_id = l.map_id
            JOIN maps.sources b ON a.source_id = b.source_id;

            CREATE INDEX ON carto.tiny_new (map_id);
            CREATE INDEX ON carto.tiny_new USING GiST (geom);

            ALTER TABLE carto.tiny RENAME TO tiny_old;
            ALTER TABLE carto.tiny_new RENAME TO tiny;
            DROP TABLE carto.tiny_old;
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

        insert = "INSERT INTO carto.%(target)s_new (map_id, orig_id, source_id, scale, name, strat_name, age, lith, descrip, comments, t_int_id, t_int, best_age_top, b_int_id, b_int, best_age_bottom, color, unit_ids, strat_name_ids, lith_ids, geom) " % {"target": target}

        sql = ["""DROP TABLE IF EXISTS carto.%(target)s_new; CREATE TABLE carto.%(target)s_new (
            map_id integer,
            orig_id integer,
            source_id integer,
            scale text,
            name text,
            strat_name text,
            age text,
            lith text,
            descrip text,
            comments text,
            t_int_id integer,
            t_int text,
            best_age_top numeric,
            b_int_id integer,
            b_int text,
            best_age_bottom numeric,
            color text,
            unit_ids integer[],
            strat_name_ids integer[],
            lith_ids integer[],
            geom geometry
        );""" % {"target": target}]


        # from top to bottom:
        filter_types = ["sources.scale = '%(target)s'::text AND sources.priority = True"  % {"target": target},
         "sources.scale = '%(target)s'::text AND sources.priority = False"  % {"target": target},
         "'%(target)s'::text = ANY(display_scales) AND sources.priority = True AND sources.scale != '%(target)s'::text"  % {"target": target},
         "'%(target)s'::text = ANY(display_scales) AND sources.priority = False AND sources.scale != '%(target)s'::text" % {"target": target},
         "sources.scale = '%(below)s'::text AND sources.priority = True" % {"below": below},
         "sources.scale = '%(below)s'::text AND sources.priority = False" % {"below": below},
         "'%(below)s'::text = ANY(display_scales) AND sources.priority = True AND sources.scale != '%(below)s'::text" % {"below": below},
         "'%(below)s'::text = ANY(display_scales) AND sources.priority = False AND sources.scale != '%(below)s'::text" % {"below": below}]


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
            DELETE FROM carto.%(target)s_new WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
            CREATE INDEX ON carto.%(target)s_new (map_id);
            CREATE INDEX ON carto.%(target)s_new USING GiST (geom);
            ALTER TABLE carto.%(target)s RENAME TO %(target)s_old;
            ALTER TABLE carto.%(target)s_new RENAME TO %(target)s;
            DROP TABLE carto.%(target)s_old;
        """, {
            "target": target
        })
        connection.commit()
        sys.exit()


    end = time.time()
    print 'Created carto.%s in %s s' % (arguments.the_scale, int(end - start))
