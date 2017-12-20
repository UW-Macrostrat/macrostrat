from ..base import Base
from rgeom import RGeom
from web_geom import WebGeom
from burwell_lookup import BurwellLookup
from ..match_scripts import strat_names
from ..match_scripts import units
from carto import Carto
from carto_lines import CartoLines
import sys

class MapSource(Base):
    """
    macrostrat process map_source <source_id>:
        Run all the necessary scripts for ingesting a given map into burwell.
        Equivalent to running the following commands (in order):
            + macrostrat process rgeom <source_id>
            + macrostrat process web_geom <source_id>
            + macrostrat match strat_names <source_id>
            + macrostrat match units <source_id>
            + macrostrat process burwell_lookup <source_id>
            + macrostrat process carto <source_id>
            + macrostrat process carto_lines <source_id>

    Usage:
      macrostrat process map_source <source_id>
      macrostrat process map_source -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat process map_source 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """
    meta = {
        'mariadb': True,
        'pg': True,
        'usage': """
            Adds a given source to the proper carto line tables.
        """,
        'required_args': {
            'source_id': 'A valid source_id'
        }
    }
    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def build(self, source_id):
        if source_id == '--help' or source_id == '-h':
            print MapSource.__doc__
            sys.exit()

        config = {
            'pg': self.pg['raw_connection'],
            'mariadb': self.mariadb['raw_connection'],
            'credentials': self.credentials
        }
        # rgeom = RGeom(config)
        # rgeom.build(source_id)
        #
        # web_geom = WebGeom(config)
        # web_geom.build(source_id)

        sn = strat_names(config)
        sn.build(source_id)

        u = units(config)
        u.build(source_id)

        burwell_lookup = BurwellLookup(config)
        burwell_lookup.build(source_id)

        carto = Carto(config)
        carto.build(source_id)

        carto_lines = CartoLines(config)
        carto_lines.build(source_id)
