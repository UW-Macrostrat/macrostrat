from .base import Base
import sys
import datetime
from psycopg2.extensions import AsIs
import process_scripts

class Process(Base):
    """
    macrostrat process <command> <source_id>:
        Scripts for processing geologic map data

    Available commands:
        burwell_lookup <source_id> - Refresh the appropriate lookup tables for a given map source
        carto_lines <source_id> - Refresh the table carto.lines_<scale> for a given map source
        carto <source_id> - Refresh the table carto.<scale> for a given map source
        rgeom <source_id> - Update the field `rgeom` in maps.sources for a given map source
        web_geom <source_id> - Update the field `web_geom` in maps.sources for a given map source
        tesselate <options> - Create new voronoi polygons for columns
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

        #if (len(self.args) - 2) != len(script.meta['required_args']) or len(self.args) == 2:
        if (len(self.args) - 2) != len(script.meta['required_args']) and cmd != 'tesselate':
            print 'You are missing a required argument for this command. The following arguments are required:'
            for arg in script.meta['required_args']:
                print '     + %s - %s' % (arg, script.meta['required_args'][arg])
            sys.exit()


        if script.meta['mariadb'] and script.meta['pg']:
            script(self.mariadb['raw_connection'], self.pg['raw_connection'])
        elif script.meta['mariadb'] and not script.meta['pg']:
            script(self.mariadb['raw_connection'])
        elif script.meta['pg'] and not script.meta['mariadb']:
            script(self.pg['raw_connection'])
        else:
            print 'wtf'

        script.build(self.args[2:])
