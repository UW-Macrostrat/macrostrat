import argparse
import psycopg2
import psycopg2.extras
from psycopg2.extensions import AsIs
from subprocess import call
import sys
import os
import datetime
import yaml

with open('./credentials.yml', 'r') as f:
    credentials = yaml.load(f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
    description="Process a burwell source. Matches to macrostrat units, refreshes lookup tables, and populates rgeom",
    epilog="Example usage: python match.py --source_id 2")

    parser.add_argument("-s", "--source_id", dest="source_id",
    default="0", type=str, required=True,
    help="The ID of the desired source to match")

    arguments = parser.parse_args()

    connection = psycopg2.connect(dbname="burwell", user=credentials["pg_user"], host=credentials["pg_host"], port=credentials["pg_port"])
    cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Validate params!
    # Valid source_id
    cursor.execute("SELECT source_id FROM maps.sources")
    sources = cursor.fetchall()
    source_ids = [source['source_id'] for source in sources]
    if int(arguments.source_id) not in source_ids:
        print "Invalid source_id argument. Source ID ", arguments.source_id, " was not found in maps.sources"
        sys.exit(1)

    # Find scale table
    scale = ""
    for scale_table in ["tiny", "small", "medium", "large"]:
        cursor  .execute("SELECT * FROM maps.%(table)s WHERE source_id = %(source_id)s LIMIT 1", {
          "table": AsIs(scale_table),
          "source_id": arguments.source_id
        })
        if cursor.fetchone() is not None:
          scale = scale_table
          break

    if len(scale) < 1:
        print "Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again."
        sys.exit(1)

    print 'Starting at ', str(datetime.datetime.now())

    # Build rgeom
    print '| | | | | Building rgeom...'
    call(['python utils/rgeom.py %s' % (arguments.source_id, ) ], shell=True)
    print '| | | | | Done building rgeom | | | | |'

    # Build web_geom
    print '| | | | | Building web_geom...'
    call(['python utils/web_geom.py %s' % (arguments.source_id, ) ], shell=True)
    print '| | | | | Done building web_geom | | | | |'

    # Match
    print '| | | | | Matching stratigraphic names...'
    call(['python matching/strat_name_match.py --source_id %s' % (arguments.source_id, )], shell=True)
    print '| | | | | Done matching stratigraphic names| | | | |'

    print '| | | | | Matching macrostrat units...'
    call(['python matching/match_units.py --source_id %s' % (arguments.source_id, )], shell=True)
    print '| | | | | Done matching macrostrat units| | | | |'

    # Refresh lookup tables
    print '| | | | | Refreshing lookup tables...'
    call(['python setup/refresh_lookup.py %s' % (arguments.source_id, ) ], shell=True)
    print '| | | | | Done refreshing lookup tables | | | | |'

    # Refresh carto lines
    print '| | | | | Adding to carto.lines...'
    call(['node utils/updateCartoLines.js %s' % (arguments.source_id, )], shell=True)
    print '| | | | | Done adding to carto.lines | | | | | '

    # Refresh carto
    print '| | | | | Adding to carto...'
    call(['node utils/updateCarto.js %s' % (arguments.source_id, )], shell=True)
    print '| | | | | Done adding to carto | | | | | '

    # Make tiles
    print '| | | | | Rolling tiles...'
    call(['node tiles/simple_seed.js --source_id %s' % (arguments.source_id, )], shell=True)
    print '| | | | | Done rolling tiles | | | | | '
