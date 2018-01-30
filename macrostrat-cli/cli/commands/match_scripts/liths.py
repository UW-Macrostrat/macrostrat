from psycopg2.extensions import AsIs
from psycopg2.extras import RealDictCursor
import time
import datetime
import sys
from ..base import Base

class Liths(Base):
    """
    macrostrat match liths <source_id>:
        Match a given map source to Macrostrat lithologies.
        Populates the table maps.legend_liths.
        Uses all available fields of matching, including lith, name, strat_name, descrip, and comments.

    Usage:
      macrostrat match liths <source_id>
      macrostrat match liths -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat match liths 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """
    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Matches burwell polygons to macrostrat liths
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }

    source_id = None

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def do_work(self, field):
        self.pg['cursor'].execute('''
            INSERT INTO maps.legend_liths (legend_id, lith_id, basis_col)
            SELECT legend_id, liths.id, %(basis)s
            FROM maps.legend, macrostrat.liths
            WHERE source_id = %(source_id)s
             AND %(field)s ~* concat('\y', liths.lith, '\y')
        ''', {
            'source_id': self.source_id,
            'basis': field,
            'field': AsIs(field)
        })
        self.pg['connection'].commit()

    def run(self, source_id):
        if source_id == '--help' or source_id == '-h':
            print Liths.__doc__
            sys.exit()

        start = time.time()
        Liths.source_id = source_id
        # Validate params!
        # Valid source_id
        self.pg['cursor'].execute('''
            SELECT source_id
            FROM maps.sources
            WHERE source_id = %(source_id)s
        ''', {
            'source_id': source_id
        })
        result = self.pg['cursor'].fetchone()
        if result is None:
            print 'Invalid source_id. %s was not found in maps.sources' % (source_id, )
            sys.exit(1)

        # Find scale table
        scale = ''
        for scale_table in ['tiny', 'small', 'medium', 'large']:
          self.pg['cursor'].execute('''
            SELECT map_id
            FROM maps.%(table)s
            WHERE source_id = %(source_id)s
            LIMIT 1
        ''', {
            'table': AsIs(scale_table),
            'source_id': source_id
          })
          if self.pg['cursor'].fetchone() is not None:
            scale = scale_table
            break

        if len(scale) == 0:
          print 'Provided source_id not found in maps.small, maps.medium, or maps.large. Please insert it and try again.'
          sys.exit(1)

        # Clean up
        self.pg['cursor'].execute("""
          DELETE FROM maps.legend_liths
          WHERE legend_id IN (
            SELECT legend_id
            FROM maps.legend
            WHERE source_id = %(source_id)s
          )
          AND basis_col NOT LIKE 'manual%%'
        """, {
          'source_id': source_id
        })
        self.pg['connection'].commit()

        print '        + Done cleaning up'


        # Fields in burwell to match on
        fields = ['lith', 'strat_name', 'name', 'descrip', 'comments']

        # Filter null fields
        self.pg['cursor'].execute("""
        SELECT
            count(distinct lith)::int AS lith,
            count(distinct strat_name)::int AS strat_name,
            count(distinct name)::int AS name,
            count(distinct descrip)::int AS descrip,
            count(distinct comments)::int AS comments
        FROM maps.%(scale)s where source_id = %(source_id)s;
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        result = self.pg['cursor'].fetchone()

        for key, val in result._asdict().iteritems():
            if val == 0:
                field_name = key
                fields = [ d for d in fields if d != key]
                print '        + Excluding %s because it is null' % (field_name, )


        # Insert a new task for each matching field into the queue
        for field in fields:
            Liths.do_work(self, field)
