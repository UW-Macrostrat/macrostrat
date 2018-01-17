from ..base import Base
from rgeom import RGeom
from web_geom import WebGeom
from burwell_lookup import BurwellLookup
from ..match_scripts import strat_names
from ..match_scripts import units
from carto import Carto
from carto_lines import CartoLines
from ..seed import Seed
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

    def run(self, source_id):
        if source_id == '--help' or source_id == '-h':
            print MapSource.__doc__
            sys.exit()

        rgeom = RGeom({})
        rgeom.run(source_id)

        web_geom = WebGeom({})
        web_geom.run(source_id)

        sn = strat_names({})
        sn.run(source_id)

        u = units({})
        u.run(source_id)

        burwell_lookup = BurwellLookup({})
        burwell_lookup.run(source_id)

        carto = Carto({})
        carto.run(source_id)

        carto_lines = CartoLines({})
        carto_lines.run(source_id)

        seed = Seed({}, True, source_id )
        seed.run()
