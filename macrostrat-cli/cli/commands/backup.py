from .base import Base
import sys
from subprocess import call
import datetime
import os
from psycopg2.extensions import AsIs
cwd = os.getcwd()

class Backup(Base):
    '''
    macrostrat backup <database or source_id>:
        Create a backup/dump of a given database or map source.
        In the case of a source, a pg_dump that first removes all instances of
        the source from the database. DELETES DATA from:
            - public.lookup_<scale>
            - maps.map_liths
            - maps.map_strat_names
            - maps.map_units
            - sources.<primary_table>
            - sources.<primary_line_table>
            - maps.sources
            - lines.<scale>
            - points.points
            - carto_new.<scale>
            - carto_new.lines_<scale>
        The source dump is intended to be used to move sources between databases
        on different machines (dev to production, laptop to dev).

    Usage:
      macrostrat backup <database or source_id>
      macrostrat backup -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat backup 123
      macrostrat backup burwell
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
        scaleIsIn = {
            'tiny': ['tiny'],
            'small': ['small', 'medium'],
            'medium': ['small', 'medium', 'large'],
            'large': ['large']
        }

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
                COPY (SELECT * FROM maps.sources WHERE source_id = %(source_id)s) TO '%(cwd)s/temp_sources.tsv' WITH ENCODING 'UTF8'
            """, {'source_id': self.args[1], 'cwd': AsIs(cwd) })
            call(['echo "COPY maps.sources FROM stdin;" | cat - temp_sources.tsv > sources.tsv && echo "\.\n" >> sources.tsv && rm -f temp_sources.tsv'], shell=True)

            # maps.scale
            self.pg['cursor'].execute("""
                COPY (SELECT * FROM maps.%(scale)s WHERE source_id = %(source_id)s) TO '%(cwd)s/temp_scale.tsv' WITH ENCODING 'UTF8'
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1], 'cwd': AsIs(cwd) })
            call(['echo "COPY maps.%s FROM stdin;" | cat - temp_scale.tsv > scale.tsv && echo "\.\n" >> scale.tsv && rm -f temp_scale.tsv' % (source_info.scale, )], shell=True)

            # lines.scale
            self.pg['cursor'].execute("""
                COPY (SELECT * FROM lines.%(scale)s WHERE source_id = %(source_id)s) TO '%(cwd)s/temp_lines.tsv' WITH ENCODING 'UTF8'
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1], 'cwd': AsIs(cwd) })
            call(['echo "COPY lines.%s FROM stdin;" | cat - temp_lines.tsv > lines.tsv && echo "\.\n" >> lines.tsv && rm -f temp_lines.tsv' % (source_info.scale, )], shell=True)

            # maps.map_liths
            self.pg['cursor'].execute("""
                COPY ( SELECT * FROM maps.map_liths
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )) TO '%(cwd)s/temp_map_liths.tsv' WITH ENCODING 'UTF8'
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
            call(['echo "COPY maps.map_liths FROM stdin;" | cat - temp_map_liths.tsv > map_liths.tsv && echo "\.\n" >> map_liths.tsv && rm -f temp_map_liths.tsv'], shell=True)

            # maps.map_strat_names
            self.pg['cursor'].execute("""
                COPY (SELECT * FROM maps.map_strat_names
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )) TO '%(cwd)s/temp_strat_names.tsv' WITH ENCODING 'UTF8'
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
            call(['echo "COPY maps.map_strat_names FROM stdin;" | cat - temp_strat_names.tsv > strat_names.tsv && echo "\.\n" >> strat_names.tsv && rm -f temp_strat_names.tsv'], shell=True)

            # maps.map_units
            self.pg['cursor'].execute("""
                COPY (SELECT * FROM maps.map_units
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )) TO '%(cwd)s/temp_map_units.tsv' WITH ENCODING 'UTF8'
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
            call(['echo "COPY maps.map_units FROM stdin;" | cat - temp_map_units.tsv > map_units.tsv && echo "\.\n" >> map_units.tsv && rm -f temp_map_units.tsv'], shell=True)

            # points.points
            self.pg['cursor'].execute("""
                COPY (SELECT * FROM points.points
                WHERE source_id = %(source_id)s) TO '%(cwd)s/temp_points.tsv' WITH ENCODING 'UTF8'
            """, { 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
            call(['echo "COPY points.points FROM stdin;" | cat - temp_points.tsv > points.tsv && echo "\.\n" >> points.tsv && rm -f temp_points.tsv'], shell=True)

            # public.lookup_scale
            self.pg['cursor'].execute("""
                COPY (SELECT * FROM public.lookup_%(scale)s
                WHERE map_id IN (
                    SELECT map_id
                    FROM maps.%(scale)s
                    WHERE source_id = %(source_id)s
                )) TO '%(cwd)s/temp_lookup.tsv' WITH ENCODING 'UTF8'
            """, { 'scale': AsIs(source_info.scale), 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
            call(['echo "COPY public.lookup_%s FROM stdin;" | cat - temp_lookup.tsv > lookup.tsv && echo "\.\n" >> lookup.tsv && rm -f temp_lookup.tsv' % (source_info.scale, )], shell=True)

            carto_tables = ''
            carto_cmd = 'cat '
            for scale in scaleIsIn[source_info.scale]:
                self.pg['cursor'].execute("""
                    COPY (SELECT * FROM carto_new.%(scale)s
                    WHERE ST_Intersects(geom, (
                        SELECT web_geom
                        FROM maps.sources
                        WHERE source_id = %(source_id)s
                    ))) TO '%(cwd)s/temp_carto_%(scale)s.tsv' WITH ENCODING 'UTF8'
                """, { 'scale': AsIs(scale), 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
                call(['echo "COPY carto_new.%s FROM stdin;" | cat - temp_carto_%s.tsv > carto_%s.tsv && echo "\.\n" >> carto_%s.tsv && rm -f temp_carto_%s.tsv' % (scale, scale, scale, scale, scale )], shell=True)

                self.pg['cursor'].execute("""
                    COPY (SELECT * FROM carto_new.lines_%(scale)s
                    WHERE ST_Intersects(geom, (
                        SELECT web_geom
                        FROM maps.sources
                        WHERE source_id = %(source_id)s
                    ))) TO '%(cwd)s/temp_carto_lines_%(scale)s.tsv' WITH ENCODING 'UTF8'
                """, { 'scale': AsIs(scale), 'source_id': self.args[1], 'cwd': AsIs(cwd)  })
                call(['echo "COPY carto_new.lines_%s FROM stdin;" | cat - temp_carto_lines_%s.tsv > carto_lines_%s.tsv && echo "\.\n" >> carto_lines_%s.tsv && rm -f temp_carto_lines_%s.tsv' % (scale, scale, scale, scale, scale )], shell=True)

                # bookkeeping for the giant command
                carto_cmd += "<(cat %s/export_scripts/delete_carto.sql | sed 's/::source_id::/%s/g; s/::scale::/%s/g')" % ( os.path.dirname(__file__), self.args[1], scale, )

                carto_tables += 'carto_%s.tsv carto_lines_%s.tsv' % (scale, scale, )

            call("cat <(cat %s/export_scripts/delete.sql | sed 's/::source_id::/%s/g; s/::scale::/%s/g; s/::primary_table::/%s/g; s/::primary_line_table::/%s/g') <(pg_dump -O -x -c -t sources.%s -t sources.%s -U %s -h %s -p %s burwell | cat - sources.tsv scale.tsv lines.tsv map_liths.tsv strat_names.tsv map_units.tsv points.tsv lookup.tsv) <(%s) <(cat %s) | gzip > %s.%s.sql.gz && rm -f *.tsv" % ( os.path.dirname(__file__), self.args[1], source_info.scale, source_info.primary_table, source_info.primary_line_table, source_info.primary_table, source_info.primary_line_table, self.credentials['pg_user'], self.credentials['pg_host'], self.credentials['pg_port'], carto_cmd, carto_tables, today, source_info.name.replace(' ', '_')), shell=True, executable='/bin/bash')

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
