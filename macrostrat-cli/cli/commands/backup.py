from .base import Base
import sys
from subprocess import call
import datetime
import os

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
            # maps.sources

            # maps.scale

            # lines.scale

            # maps.map_liths

            # maps.map_strat_names

            # maps.map_units

            # sources.<primary_table>

            # sources.primary_table_lines

            # points.points
            print 'Backup source'
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
