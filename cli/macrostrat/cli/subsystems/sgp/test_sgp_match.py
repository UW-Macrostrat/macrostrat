from pytest import mark

from . import get_sgp_db
from .match import DatabaseConfig, match_sgp_data


# Note: these tests have to be outside the macrostrat.cli package
# because of how the macrostrat.core.config module is imported.
@mark.slow
def test_match_sgp_data(db):

    databases = DatabaseConfig(db, get_sgp_db())

    print(databases.macrostrat.engine.url)
    print(databases.sgp.engine.url)

    res = match_sgp_data(None, sample=5, databases=databases)
    assert res is not None
    assert len(res) == 5
