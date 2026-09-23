"""Fill a map source's legend entries from its matches.

Each step is one statement file under `procedures/legend-lookup/`, updating a
group of `maps.legend` columns for the source; `assign_colors` then nudges the
base colours apart.
"""

from psycopg2.sql import Identifier
from rich import print

from macrostrat.database import Database

from ..database import sql_file
from ..utils import MapInfo
from ..utils.legend_color import LegendRow, assign_colors
from .lookup import source_scale

#: The legend-lookup steps, in the order they run. Later steps read what earlier
#: ones wrote: `concepts` reads `unit_ids` and `strat_name_ids`, and `ages`
#: reads `unit_ids`.
STEPS = ["unit-ids", "strat-name-ids", "liths", "concepts", "ages"]


def legend_lookup(db: Database, source: MapInfo):
    """Refresh one source's legend entries from its unit, strat-name and lith matches."""
    scale = source_scale(db, source.id)
    params = {"source_id": source.id, "scale_table": Identifier("maps", scale)}
    for step in STEPS:
        db.run_sql(sql_file("legend-lookup/" + step), params)

    # Nudge same-age units apart. Variants are chosen from each legend's place
    # and size, so two maps of the same ground agree; see utils/legend_color.
    # One read and one write per map -- this used to be an UPDATE per legend
    # row, followed by a name-based homogenization sweep that rewrote every
    # other map at a compatible scale.
    rows = color_inputs(db, source.id, scale)
    changes = assign_colors(rows)
    write_colors(db, changes)
    print(f"Shifted {len(changes)} of {len(rows)} legend colors")


def color_inputs(db: Database, source_id: int, scale: str) -> list[LegendRow]:
    """Each legend entry's base colour and age, and the place and size of its polygons.

    Nearly all of the cost is the spheroidal area -- 14.8 of 15.7 s on SGMC --
    and it cannot be cheapened without moving `area_km`, which keys the colour.
    """
    rows = db.run_query(
        """
        SELECT
          l.legend_id,
          l.color,
          l.best_age_top,
          l.best_age_bottom,
          ST_X(ST_Centroid(ST_Extent(q.geom))) AS cx,
          ST_Y(ST_Centroid(ST_Extent(q.geom))) AS cy,
          sum(ST_Area(q.geom::geography)) / 1e6 AS area_km
        FROM maps.legend l
        LEFT JOIN maps.map_legend ml ON ml.legend_id = l.legend_id
        LEFT JOIN {scale_table} q
          ON q.map_id = ml.map_id AND q.source_id = l.source_id
        WHERE l.source_id = :source_id
        GROUP BY l.legend_id
        """,
        {"source_id": source_id, "scale_table": Identifier("maps", scale)},
    ).all()
    return [
        LegendRow(
            legend_id=r.legend_id,
            color=r.color,
            best_age_top=_as_float(r.best_age_top),
            best_age_bottom=_as_float(r.best_age_bottom),
            cx=r.cx,
            cy=r.cy,
            area_km=_as_float(r.area_km),
        )
        for r in rows
    ]


def write_colors(db: Database, changes: dict[int, str]):
    """Set `maps.legend.color` for each `{legend_id: color}`."""
    if not changes:
        return
    db.run_sql(
        """
        UPDATE maps.legend l
        SET color = v.color
        FROM unnest(CAST(:legend_ids AS integer[]), CAST(:colors AS text[]))
          AS v(legend_id, color)
        WHERE l.legend_id = v.legend_id
        """,
        {"legend_ids": list(changes.keys()), "colors": list(changes.values())},
    )


def _as_float(value):
    if value is None:
        return None
    return float(value)
