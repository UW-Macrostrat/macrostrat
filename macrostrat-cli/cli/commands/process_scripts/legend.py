from ..base import Base
from psycopg2.extensions import AsIs
import sys

class Legend(Base):
    """
    macrostrat process legend <source_id>:
        Insert/update a source's records in maps.legend and maps.map_legend

    Usage:
      macrostrat process legend <source_id>
      macrostrat process legend -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat process legend 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    meta = {
        'mariadb': False,
        'pg': True,
        'usage': """
            Refresh the appropriate lookup tables for a given map source
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)


    def run(self, source_id):
        if len(source_id) == 0 or source_id[0] == '--help' or source_id[0] == '-h':
            print Legend.__doc__
            sys.exit()

        source_id = source_id[0]

        self.pg['cursor'].execute('''
            SELECT scale
            FROM maps.sources
            WHERE source_id = %(source_id)s
        ''', { 'source_id': source_id })
        scale = self.pg['cursor'].fetchone()

        if scale is None:
            print 'Source ID %s was not found in maps.sources' % (source_id, )
            sys.exit(1)

        if scale[0] is None:
            print 'Source ID %s is missing a scale' % (source_id, )
            sys.exit(1)

        scale = scale[0]

        # Clean up
        self.pg['cursor'].execute("""
          DELETE FROM maps.map_legend WHERE map_id IN (
            SELECT map_id
            FROM maps.%(scale)s
            WHERE source_id = %(source_id)s
          )
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
          INSERT INTO maps.legend (source_id, name, strat_name, age, lith, descrip, comments, b_interval, t_interval)
          SELECT DISTINCT ON (q.name, q.strat_name, q.age, q.lith, q.descrip, q.comments, q.b_interval, q.t_interval) %(source_id)s, q.name, q.strat_name, q.age, q.lith, q.descrip, q.comments, q.b_interval, q.t_interval
            FROM maps.%(scale)s q
            LEFT JOIN maps.legend ON
                trim(COALESCE(legend.name, '')) = trim(COALESCE(q.name, '')) AND
                trim(COALESCE(legend.strat_name, '')) = trim(COALESCE(q.strat_name, '')) AND
                trim(COALESCE(legend.age, '')) = trim(COALESCE(q.age, '')) AND
                trim(COALESCE(legend.lith, '')) = trim(COALESCE(q.lith, '')) AND
                trim(COALESCE(legend.descrip, '')) = trim(COALESCE(q.descrip, '')) AND
                trim(COALESCE(legend.comments, '')) = trim(COALESCE(q.comments, '')) AND
                COALESCE(legend.b_interval, -999) = COALESCE(q.b_interval, -999) AND
                COALESCE(legend.t_interval, -999) = COALESCE(q.t_interval, -999) AND
                legend.source_id = %(source_id)s
            WHERE q.source_id = %(source_id)s
            AND legend_id IS NULL;
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()

        self.pg['cursor'].execute("""
          INSERT INTO maps.map_legend (legend_id, map_id)
          SELECT legend_id, map_id
          FROM maps.%(scale)s m
          JOIN maps.legend ON
            legend.source_id = m.source_id AND
            trim(COALESCE(legend.name, '')) = trim(COALESCE(m.name, '')) AND
            trim(COALESCE(legend.strat_name, '')) = trim(COALESCE(m.strat_name, '')) AND
            trim(COALESCE(legend.age, '')) = trim(COALESCE(m.age, '')) AND
            trim(COALESCE(legend.lith, '')) = trim(COALESCE(m.lith, '')) AND
            trim(COALESCE(legend.descrip, '')) = trim(COALESCE(m.descrip, '')) AND
            trim(COALESCE(legend.comments, '')) = trim(COALESCE(m.comments, '')) AND
            COALESCE(legend.b_interval, -999) = COALESCE(m.b_interval, -999) AND
            COALESCE(legend.t_interval, -999) = COALESCE(m.t_interval, -999)
          WHERE m.source_id = %(source_id)s;
        """, {
            'scale': AsIs(scale),
            'source_id': source_id
        })
        self.pg['connection'].commit()
