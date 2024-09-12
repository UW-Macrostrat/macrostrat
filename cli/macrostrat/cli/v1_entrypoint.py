"""
macrostrat-cli: a command-line interface for working with Macrostrat data[bases]

Usage:
  macrostrat v1 rebuild <table>
  macrostrat v1 match <cmd> <source_id>
  macrostrat v1 backup <db>
  macrostrat v1 process <cmd> <source_id>
  macrostrat v1 schlep <table>
  macrostrat v1 export [coming soon]
  macrostrat v1 -h | --help
  macrostrat v1 --version
Options:
  -h --help                         Show this screen.
  --version                         Show version.
Examples:
  macrostrat rebuild lookup_strat_names
Help:
  For help using this tool, please open an issue on the Github repository:
  https://github.com/UW-Macrostrat/utils
"""

import sys

import click

# CLI with unprocessed arguments


@click.command(name="v1")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def v1_cli(args):
    """Macrostrat CLI v1 commands"""
    # import all available commands
    from . import __version__ as VERSION
    from . import commands
    from .database import mariaConnection, pgConnection

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

    script = script({"pg": pgConnection, "mariadb": mariaConnection}, *args)

    if len(args) == 1 or args[1] == "--help" or args[1] == "-h":
        # Print script help
        print((script.__doc__))
        sys.exit()

    script.run()
