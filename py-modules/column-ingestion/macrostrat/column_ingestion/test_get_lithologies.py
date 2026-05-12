from pytest import approx

from .lithologies import Lithology
from .query_helpers import get_liths_for_unit


def test_get_liths_for_existing_unit(env_db):
    """Get lithologies for an existing unit."""
    unit_id = 39600

    unit = env_db.run_query(
        "SELECT id, col_id, strat_name FROM macrostrat.units WHERE id = :id",
        dict(id=unit_id),
    ).one_or_none()
    assert unit is not None, f"No unit found with id {unit_id}"
    assert unit.strat_name == "Maieberg Fm"
    assert unit.col_id == 1740
    _liths = get_liths_for_unit(env_db, unit_id)
    assert len(_liths) == 3
    dol = get_lith(_liths, "dolomite")
    assert dol is not None
    assert dol.dom == "dom"
    assert is_approx(dol.prop, 0.7143)

    ls = get_lith(_liths, "limestone")
    assert ls is not None
    assert ls.dom == "sub"
    assert is_approx(ls.prop, 0.1429)
    sh = get_lith(_liths, "shale")
    assert sh is not None
    assert sh.dom == "sub"
    assert is_approx(sh.prop, 0.1429)
    assert sum(lith.prop for lith in _liths if lith.prop is not None) == approx(
        1, abs=0.01
    )


def is_approx(a, b):
    return float(a) == approx(b)


def get_lith(_liths: set[Lithology], lith_name: str):
    for lith in _liths:
        if lith.name == lith_name:
            return lith
    return None
