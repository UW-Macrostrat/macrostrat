"""
macrostrat-cli: a command-line interface for working with Macrostrat data[bases]

Usage:
  macrostrat rebuild <table>
  macrostrat match <cmd> <source_id>
  macrostrat backup <db>
  macrostrat process <cmd> <source_id>
  macrostrat schlep <table>
  macrostrat seed <source_id>
  macrostrat export [coming soon]
  macrostrat maps [New map ingestion CLI, if installed]
  macrostrat update-db    Update the database to the latest version
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
from .database import pgConnection, mariaConnection
import sys
from typer import Typer

from .v2_commands.upgrade_db import upgrade_db

# import all available commands
from . import commands

app = Typer()

app.command(name="upgrade-db")(upgrade_db)


def main():
    """Main CLI entrypoint."""
    # No parameters
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit()

    if sys.argv[1] == "--help" or sys.argv[1] == "-h":
        print(__doc__)
        sys.exit()

    if sys.argv[1] == "--version":
        print(("macrostrat-cli - %s" % (VERSION,)))
        sys.exit()

    if sys.argv[1] == "maps":
        print("Error: map ingestion CLI is not installed")
        sys.exit()

    if sys.argv[1] == "update-db":
        sys.argv = sys.argv[1:]
        app()

    cmd = sys.argv[1]
    if cmd not in dir(commands):
        print(('Error: command "%s" is not valid' % (cmd,)))
        sys.exit()

    # Get the class associated with the provided table name
    script = getattr(commands, cmd)

    script = script({"pg": pgConnection, "mariadb": mariaConnection}, *sys.argv[1:])

    if len(sys.argv) == 2 or sys.argv[2] == "--help" or sys.argv[2] == "-h":
        print((script.__doc__))
        sys.exit()

    script.run()
