from ..base import Base
from rgeom import RGeom
from web_geom import WebGeom
from burwell_lookup import BurwellLookup
from ..match_scripts import strat_names
from ..match_scripts import units
from carto import Carto
from carto_lines import CartoLines

class MapSource(Base):
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
