from pytest import mark

from macrostrat.cli.subsystems.sgp.match import import_sgp_data


@mark.slow
def test_match_sgp_data(db):

    res = import_sgp_data(None, sample=5)
    assert res is not None
    assert len(res) == 5
