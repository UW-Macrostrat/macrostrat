"""
macrostrat match:

Usage:
  macrostrat match <script> <source_id>
  macrostrat match -h | --help
Options:
  -h --help                         Show this screen.
  --version                         Show version.
Examples:
  macrostrat match strat_names 123
Help:
  For help using this tool, please open an issue on the Github repository:
  https://github.com/UW-Macrostrat/macrostrat-cli
"""


from .base import Base
import match_scripts
import sys

class Match(Base):
    def do_build(self, table):
        # Get the class associated with the provided table name
        script = getattr(match_scripts, table)

        print '    Building %s' % (table, )

        if script.meta['mariadb'] and script.meta['pg']:
            script.build(self.mariadb['raw_connection'], self.pg['raw_connection'])
        elif script.meta['mariadb']:
            script.build(self.mariadb['raw_connection'])
        elif script.meta['pg']:
            script.build(self.pg['raw_connection'])
        else:
            print 'Build script does not specify connector type'
            sys.exit()

        print '       Done'

    def run(self):
        # Check if a table was provided
        if len(self.args) != 3:
            print 'Wrong number of arguments'
            sys.exit()

        # Validate the passed script
        cmd = self.args[1]
        if cmd not in dir(match_scripts) and cmd != 'all':
            print 'Invalid script'
            sys.exit()

        script = getattr(match_scripts, cmd)

        if (len(self.args) - 2) != len(script.meta['required_args']) or len(self.args) == 2:
            print 'You are missing a required argument for this command. The following arguments are required:'
            for arg in script.meta['required_args']:
                print '     + %s - %s' % (arg, script.meta['required_args'][arg])
            sys.exit()

        script(self.pg['raw_connection'])
        script.build(*self.args[2:])
