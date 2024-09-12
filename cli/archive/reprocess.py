# from cli.commands.process_scripts import map_source
# from cli.commands.process_scripts import legend
# from cli.commands.match_scripts import liths
# from cli.commands.process_scripts import burwell_lookup
from macrostrat_cli.commands.process_scripts import legend_lookup

from ..macrostrat_cli.database import mariaConnection, pgConnection

opts = {"pg": pgConnection, "mariadb": mariaConnection}

c1 = legend_lookup(opts)
pg_connection = pgConnection()
pg_cursor = pg_connection.cursor()

pg_cursor.execute(
    """
    SELECT source_id
    FROM maps.sources
    WHERE status_code = 'active'
    ORDER BY source_id
"""
)
sources = pg_cursor.fetchall()

pg_connection.close()

for source in sources:
    print(("WORKING ON %s" % (source[0],)))
    c1.run((source[0],))
