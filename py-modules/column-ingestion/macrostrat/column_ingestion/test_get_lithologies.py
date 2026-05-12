from .lithologies import LithAtt, Lithology
from macrostrat.database import Database
from pytest import approx

get_liths_sql = """
                SELECT
                    ul.unit_id,
                    ul.id AS unit_lith_id,
                    l.lith,
                    ul.lith_id,
                    l.lith_type,
                    l.lith_class,
                    ul.prop,
                    ul.comp_prop,
                    ul.mod_prop,
                    json_strip_nulls(json_agg(json_build_object('id', la.id, 'name', la.lith_att, 'type', la.att_type)) FILTER (WHERE la.id IS NOT NULL)) atts
                FROM macrostrat.unit_liths ul
                JOIN macrostrat.liths l
                ON ul.lith_id = l.id
                LEFT JOIN macrostrat.unit_liths_atts ula
                ON ul.id = ula.unit_lith_id
                LEFT JOIN macrostrat.lith_atts la
                ON ula.lith_att_id = la.id
                WHERE unit_id = :unit_id
                GROUP BY ul.unit_id, ul.id, l.lith, ul.lith_id, l.lith_type, l.lith_class, ul.prop, ul.comp_prop, ul.mod_prop; \
                """


def get_liths_for_unit(db: Database, unit_id: int) -> set[Lithology]:
    """Get lithologies for a given unit_id. This is a wrapper around the database query that returns Lithology objects instead of raw database rows."""
    lith_rows = db.run_query(get_liths_sql, dict(unit_id=unit_id)).fetchall()

    liths = set()
    for row in lith_rows:
        lith = Lithology(
            name=row.lith,
            id=row.lith_id,
            dom=row.prop,
            prop=row.comp_prop,
            attributes=(
                {LithAtt(name=att["name"], id=att["id"]) for att in row.atts}
                if row.atts is not None
                else None
            ),
        )
        liths.add(lith)
    return liths


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
