from pytest import fixture

from .strat_names import StratRank, clean_strat_name, create_ignore_list


@fixture(scope="module", autouse=True)
def lith_names(db):
    lith_names = db.run_query("SELECT lith name FROM macrostrat.liths").scalars().all()
    create_ignore_list(lith_names)


def test_clean_strat_name():
    name = "Silverton Mountain Formation"
    res = clean_strat_name(name)
    assert len(res) == 1
    res = res[0]
    assert res.name == "silverton mountain"
    assert res.rank is StratRank.Formation


def test_clean_strat_name_lith():
    name = "Noonday Dolomite"
    res = clean_strat_name(name)
    assert len(res) == 1
    res = res[0]
    assert res.name == "noonday"
    assert res.rank is None


def test_clean_strat_name_hard():
    """Test strat name cleaning on a hard name (Wagon Bed Formation)"""

    name = "Wagon Bed Formation"
    res = clean_strat_name(name)
    assert len(res) == 1
    assert res[0].name == "wagon bed"
    assert res[0].rank == StratRank.Formation


def test_clean_strat_name_multiple():
    name = "Arikaree; Wagon Bed Formation; Supai Group"
    res = clean_strat_name(name)
    assert len(res) == 3
    assert res[0].name == "arikaree"
    assert res[0].rank is None

    assert res[1].name == "wagon bed"
    assert res[1].rank == StratRank.Formation

    assert res[2].name == "supai"
    assert res[2].rank == StratRank.Group
