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
  macrostrat v2    Version 2 commands
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
from subprocess import run
import sys
import click

# import all available commands
from . import commands
from .v2_commands import app

# CLI with unprocessed arguments

@click.command(name="v1")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def v1_cli(args):
    """Macrostrat CLI v1 commands"""
    # No parameters
    if len(args) == 0:
        print(__doc__)
        sys.exit()

    if args[0] == "--help" or args[0] == "-h":
        print(__doc__)
        sys.exit()

    if args[0] == "--version":
        print(("macrostrat-cli - %s" % (VERSION,)))
        sys.exit()

    cmd = args[0]
    if cmd not in dir(commands):
        print(('Error: command "%s" is not valid' % (cmd,)))
        sys.exit()

    # Get the class associated with the provided table name
    script = getattr(commands, cmd)

    script = script({"pg": pgConnection, "mariadb": mariaConnection}, args)

    if len(args) == 1 or args[1] == "--help" or args[1] == "-h":
        # Print script help
        print((script.__doc__))
        sys.exit()

    script.run()
