"""
macrostrat rebuild:

Usage:
  macrostrat rebuild <table>
  macrostrat rebuild -h | --help
Options:
  -h --help                         Show this screen.
  --version                         Show version.
Examples:
  macrostrat rebuild lookup_strat_names
Help:
  For help using this tool, please open an issue on the Github repository:
  https://github.com/UW-Macrostrat/macrostrat-cli
"""


from .base import Base
import rebuild_scripts
import sys

class Rebuild(Base):
    """ Rebuild lookup tables, and such """
    @classmethod
    def do_build(self, table):
        # Get the class associated with the provided table name
        script = getattr(rebuild_scripts, table)

        print '    Building %s' % (table, )

        if script.meta['mariadb'] and script.meta['pg']:
            script.build(mariaConnection, pgConnection)
        elif script.meta['mariadb']:
            script.build(mariaConnection)
        elif script.meta['pg']:
            script.build(pgConnection)
        else:
            print 'Build script does not specify connector type'
            sys.exit()

        print '       Done'

    def run(self):
        # Check if a table was provided
        if len(self.args) != 1:
            print 'Please specify a table'
            for table in dir(rebuild_scripts):
                if table[:2] != '__':
                    print '   %s' % (table, )
            sys.exit()

        # Validate the passed table
        table = self.args[0]
        if table not in dir(rebuild_scripts) and table != 'all':
            print 'Invalid table'
            sys.exit()

        if table == 'all':
            tables = [ t for t in dir(rebuild_scripts) if t[:2] != '__']
            for t in tables:
                Rebuild.do_build(t)
        else:
            Rebuild.do_build(table)
