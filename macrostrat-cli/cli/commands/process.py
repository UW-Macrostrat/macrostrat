"""
macrostrat process:

Usage:
  macrostrat process <script> <source_id>
  macrostrat process -h | --help
Options:
  -h --help                         Show this screen.
  --version                         Show version.
Examples:
  macrostrat process web_geom 21
Help:
  For help using this tool, please open an issue on the Github repository:
  https://github.com/UW-Macrostrat/macrostrat-cli
"""


from .base import Base
import sys
import datetime
from psycopg2.extensions import AsIs
import process_scripts

class Process(Base):

    def run(self):
        # Check if a table was provided
        if len(self.args) == 1:
            print 'Please specify a command'
            for cmd in dir(process_scripts):
                if cmd[:2] != '__':
                    print '   %s' % (cmd, )
            sys.exit()

        # Validate the passed table
        cmd = self.args[1]
        if cmd not in dir(process_scripts):
            print 'Invalid command'
            sys.exit()

        script = getattr(process_scripts, cmd)

        if (len(self.args) - 2) != len(script.meta['required_args']) or len(self.args) == 2:
            print 'You are missing a required argument for this command. The following arguments are required:'
            for arg in script.meta['required_args']:
                print '     + %s - %s' % (arg, script.meta['required_args'][arg])
            sys.exit()

        script(self.pg['raw_connection'])
        script.build(self.args[2])
