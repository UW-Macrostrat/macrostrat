from .base import Base
import sys
from subprocess import call
import datetime
import os
from psycopg2.extensions import AsIs

class Backup(Base):
    '''
    macrostrat backup <database or source_id>:
        Create a backup/dump of a given database or map source

    Usage:
      macrostrat backup <database or source_id>
      macrostrat backup -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat match strat_names 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    '''

    def run(self):
        pg_dbs = ['rockd', 'burwell', 'alice', 'geomacro', 'wof', 'elevation']
        mariadb_dbs = ['macrostrat', 'pbdb']
        now = datetime.datetime.now()
        today = '%s.%s.%s' % (now.year, now.month, now.day)
        FNULL = open(os.devnull, 'w')

        # Check if a table was provided
        if len(self.args) != 2:
            print 'Wrong number of arguments'
            sys.exit()

        # Check if a database name or source_id was passed
        if self.args[1].isdigit():
            # Get info
            self.pg['cursor'].execute("""
                SELECT name, primary_table, primary_line_table, scale
                FROM maps.sources WHERE source_id = %(source_id)s
            """, {'source_id': self.args[1]})
            source_info = self.pg['cursor'].fetchone()

            if source_info is None:
                print 'Invalid source id. Source ID %s not found' % (self.args[1], )
                sys.exit(1)

            # maps.sources
            self.pg['cursor'].execute("""
                CREATE TABLE temp_sources AS
                SELECT * FROM maps.sources WHERE source_id = %(source_id)s
            """, {'source_id': self.args[1]})

            # maps.scale
            self.pg['cursor'].execute("""
                CREATE TABLE temp_scale AS
                SELECT * FROM maps.%(scale)s WHERE source_id = %(source_id)s
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1]})

            # lines.scale
            self.pg['cursor'].execute("""
                CREATE TABLE temp_lines AS
                SELECT * FROM lines.%(scale)s WHERE source_id = %(source_id)s
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1]})

            # maps.map_liths
            self.pg['cursor'].execute("""
                CREATE TABLE temp_liths AS
                SELECT * FROM maps.map_liths
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1] })

            # maps.map_strat_names
            self.pg['cursor'].execute("""
                CREATE TABLE temp_strat_names AS
                SELECT * FROM maps.map_strat_names
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1] })

            # maps.map_units
            self.pg['cursor'].execute("""
                CREATE TABLE temp_units AS
                SELECT * FROM maps.map_units
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1] })


            # points.points
            self.pg['cursor'].execute("""
                CREATE TABLE temp_points AS
                SELECT * FROM points.points
                WHERE source_id = %(source_id)s
            """, { 'source_id': self.args[1] })

            # public.lookup_scale
            self.pg['cursor'].execute("""
                CREATE TABLE temp_lookup AS
                SELECT * FROM public.lookup_%(scale)s
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1] })
            self.pg['connection'].commit()

            call(['pg_dump -O -x --data-only --column-inserts -t temp_sources -t temp_scale -t temp_lines -t temp_liths -t temp_strat_names -t temp_units -t temp_points -t temp_lookup -U %s -h %s -p %s burwell > temp.sql && pg_dump -O -x -c -t sources.%s -t sources.%s -U %s -h %s -p %s burwell > primary.sql && cat temp.sql primary.sql | gzip > %s.%s.sql.gz && rm temp.sql && rm primary.sql'
            % ( self.credentials['pg_user'], self.credentials['pg_host'], self.credentials['pg_port'], source_info.primary_table, source_info.primary_line_table, self.credentials['pg_user'], self.credentials['pg_host'], self.credentials['pg_port'], today, source_info.name.replace(' ', '_'))], shell=True)

            self.pg['cursor'].execute("""
                DROP TABLE temp_sources;
                DROP TABLE temp_scale;
                DROP TABLE temp_lines;
                DROP TABLE temp_liths;
                DROP TABLE temp_strat_names;
                DROP TABLE temp_units;
                DROP TABLE temp_points;
                DROP TABLE temp_lookup;
            """)
            self.pg['connection'].commit()

            print '     Dumped %s to %s.%s.sql.gz' % (source_info.name, today, source_info.name.replace(' ', '_'))
        else:
            db = self.args[1]
            if db in pg_dbs:
                if 'db' == 'burwell':
                    call(['pg_dump -O -x -T sources.etopo1 -U %s -h %s -p %s burwell | gzip > %s.burwell.sql.gz' % (self.credentials['pg_user'], self.credentials['pg_host'], self.credentials['pg_port'], today)], shell=True, stdout=FNULL)
                else:
                    call(['pg_dump -O -x -U %s -h %s -p %s %s | gzip > %s.%s.sql.gz' % (self.credentials['pg_user'], self.credentials['pg_host'], self.credentials['pg_port'], db, today, db)], shell=True, stdout=FNULL)

            elif db in mariadb_dbs:
                call(['mysqldump -u %s --password=%s -h %s -S %s %s | gzip > %s.%s.sql.gz' % (self.credentials['mysql_user'], self.credentials['mysql_passwd'], self.credentials['mysql_host'], self.credentials['mysql_socket'], db, today, db)], shell=True, stdout=FNULL)

            else:
                print ' Invalid database. The following are available:'
                print '     Postgres: '
                for db in pg_dbs:
                    print '       + %s' % (db, )
                print '     MariaDB: '
                for db in mariadb_dbs:
                    print '       + %s' % (db, )

            print '     Dumped %s to %s.%s.sql.gz' % (db, today, db)
