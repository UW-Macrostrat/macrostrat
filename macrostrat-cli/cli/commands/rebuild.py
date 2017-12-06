from .base import Base
import rebuild_scripts
import sys

class Rebuild(Base):
    '''
    macrostrat rebuild <table>
        Scripts for rebuilding lookup tables

    Available tables:
        autocomplete
        lookup_strat_names
        lookup_unit_attrs_api
        lookup_unit_intervals
        lookup_units
        pbdb_matches
        stats
        strat_name_footprints
        unit_boundaries

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
    '''

    def do_build(self, table):
        # Get the class associated with the provided table name
        script = getattr(rebuild_scripts, table)

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
        if len(self.args) != 2:
            print 'Please specify a table'
            for table in dir(rebuild_scripts):
                if table[:2] != '__':
                    print '   %s' % (table, )
            sys.exit()

        # Validate the passed table
        table = self.args[1]
        if table not in dir(rebuild_scripts) and table != 'all':
            print 'Invalid table'
            sys.exit()

        if table == 'all':
            tables = [ t for t in dir(rebuild_scripts) if t[:2] != '__']
            for t in tables:
                Rebuild.do_build(self, t)
        else:
            Rebuild.do_build(self, table)
