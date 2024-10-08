import argparse
import os
import sys
import time
from subprocess import call

import psycopg2
import yaml
from psycopg2.extensions import AsIs

with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

parser = argparse.ArgumentParser(
    description="Creat a unioned reference geometry for a given source",
    epilog="Example usage: python web_geom.py 1")

parser.add_argument(nargs="?", dest="source_id",
    default="0", type=int,
    help="The ID of the desired source to create a web geom for")

arguments = parser.parse_args()

if arguments.source_id == 0:
    sys.exit(1)

if __name__ == '__main__':
    connection = psycopg2.connect(dbname="burwell", user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'])
    cursor = connection.cursor()

    # Get the primary table of the target source
    cursor.execute("""
        WITH first as (
            select source_id, (ST_Dump(ST_Split(ST_SetSRID(rgeom, 4326), ST_SetSRID(ST_MakeLine(ST_MakePoint(-180, 90), ST_MakePoint(-180, -90)), 4326)))).geom
            FROM maps.sources
            WHERE source_id = %(source_id)s
        ),

        sides AS (
            SELECT source_id,
                CASE
                    WHEN ST_XMin(geom) < 0
                        THEN 'w'
                    ELSE 'e'
                 END as side
                 , ST_Area(geom) AS area, geom
            FROM first
            WHERE ST_Area(geom) > 0.01
        ),

        best_sides AS (
            SELECT source_id, side AS best_side, sum(area)
            FROM sides
            GROUP BY source_id, side
            ORDER BY sum desc
            LIMIT 1
        ),

        final AS(
            SELECT sides.source_id,
                CASE
                    WHEN side = best_side
                        THEN geom
                    WHEN side = 'e' AND best_side = 'w'
                        THEN ST_Translate(geom, -360, 0)
                    WHEN side = 'w' AND best_side = 'e'
                        THEN ST_Translate(geom, 360, 0)
                    END as geom
            FROM sides
            JOIN best_sides ON sides.source_id = best_sides.source_id
        )

        UPDATE maps.sources
        SET web_geom = (
            SELECT
                ST_MakeEnvelope(
                    st_xmin(ST_Collect(geom)),
                    st_ymin(ST_Collect(geom)),
                    st_xmax(ST_Collect(geom)),
                    st_ymax(ST_Collect(geom)),
                    4326
            )
         FROM final
         GROUP BY source_id
        )
        WHERE source_id = %(source_id)s;
    """, {
        "source_id": arguments.source_id
    })
    connection.commit()

    print 'Done in creating web_geom'
