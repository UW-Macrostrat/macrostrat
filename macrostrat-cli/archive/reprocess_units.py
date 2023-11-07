from ..macrostrat_cli.database import pgConnection, mariaConnection

from macrostrat_cli.commands.match_scripts import units
from macrostrat_cli.commands.process_scripts import burwell_lookup

opts = {"pg": pgConnection, "mariadb": mariaConnection}

unit_processing = units(opts)
lookup_processing = burwell_lookup(opts)


pg_connection = pgConnection()
pg_cursor = pg_connection.cursor()

pg_cursor.execute(
    """
    SELECT source_id
    FROM maps.sources
    WHERE scale = 'small'
    ORDER BY source_id
"""
)
sources = pg_cursor.fetchall()

pg_connection.close()

for source in sources:
    print(("WORKING ON %s" % (source[0],)))
    unit_processing.run(source[0])
    lookup_processing.run(source[0])
