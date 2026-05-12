"""
Helper functions for getting data from the database.
Many of these may be moved to a Macrostrat data helpers library eventually.
"""

from macrostrat.database import Database

from ..lithologies import LithAtt, Lithology

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
    GROUP BY ul.unit_id, ul.id, l.lith, ul.lith_id, l.lith_type, l.lith_class, ul.prop, ul.comp_prop, ul.mod_prop
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
