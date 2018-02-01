"""
macrostrat-cli: a command-line interface for working with Macrostrat data[bases]

Usage:
  macrostrat rebuild <table>
  macrostrat match <cmd> <source_id>
  macrostrat backup <db>
  macrostrat process <cmd> <source_id>
  macrostrat schlep <table>
  macrostrat export [coming soon]
  macrostrat -h | --help
  macrostrat --version
Options:
  -h --help                         Show this screen.
  --version                         Show version.
Examples:
  macrostrat rebuild lookup_strat_names
Help:
  For help using this tool, please open an issue on the Github repository:
  https://github.com/UW-Macrostrat/utils
"""


from . import __version__ as VERSION
import sys
import pymysql
import pymysql.cursors
from warnings import filterwarnings
import os
import psycopg2
from psycopg2.extensions import AsIs
import subprocess
import yaml
import datetime
# import all available commands
import commands

# Load the credentials file
with open(os.path.join(os.path.dirname(__file__), '../credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

# Connect to MySQL
def mariaConnection():
    # Ignore warnings from MariaDB
    filterwarnings('ignore', category = pymysql.Warning)
    return pymysql.connect(host=credentials['mysql_host'], user=credentials['mysql_user'], passwd=credentials['mysql_passwd'], db=credentials['mysql_db'], unix_socket=credentials['mysql_socket'], cursorclass=pymysql.cursors.SSDictCursor, read_timeout=180)

# Connect to Postgres
def pgConnection():
    pg_conn = psycopg2.connect(dbname=credentials['pg_db'], user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'])
    pg_conn.set_client_encoding('Latin1')
    return pg_conn


def main():
    """Main CLI entrypoint."""
    # No parameters
    if len(sys.argv) == 1:
        print __doc__
        sys.exit()

    if sys.argv[1] == '--help' or sys.argv[1] == '-h':
        print __doc__
        sys.exit()

    if sys.argv[1] == '--version':
        print 'macrostrat-cli - %s' % (VERSION, )
        sys.exit()

    cmd = sys.argv[1]
    if cmd not in dir(commands):
        print 'Error: command "%s" is not valid' % (cmd, )
        sys.exit()

    # Get the class associated with the provided table name
    script = getattr(commands, cmd)

    script = script({
        'pg': pgConnection,
        'mariadb': mariaConnection,
        'credentials': credentials
    }, *sys.argv[1:])


    if len(sys.argv) == 2 or sys.argv[2] == '--help' or sys.argv[2] == '-h':
        print script.__doc__
        sys.exit()

    script.run()
