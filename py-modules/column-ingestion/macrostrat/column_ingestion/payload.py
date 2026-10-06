"""The ingested columns read back as the web API would serve them.

A dry run writes everything inside a transaction that is then rolled back, so the only
way to show what the database *would* hold — filled values, resolved lithologies, the
age model's surfaces — is to read it back before the rollback. The result follows the
shapes the column editor already consumes: units as the v2 API's `/units?response=long`
rows, surfaces as its `/age_model` rows, plus the column summaries.

Ids assigned inside a rolled-back transaction mean nothing afterwards, so on a dry run
they are renumbered to negative provisional ids, which the editor treats as "not yet
written".
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text

from .columns.parse import Column
from .intervals import get_interval_by_id


def build_payload(db, columns: list[Column], *, provisional: bool) -> dict:
    """Everything the editor needs to show these columns, read back from the session."""
    col_ids = [col.id for col in columns if col.id is not None and col.id > 0]
    unit_rows = _fetch_units(db, col_ids)
    liths = _fetch_liths(db, col_ids)
    environs = _fetch_environs(db, col_ids)
    notes = _fetch_notes(db, col_ids)
    boundaries = _fetch_boundaries(db, col_ids)

    parsed_units = {unit.id: unit for col in columns for unit in col.units}
    ages = _unit_ages(boundaries)

    units = []
    for row in unit_rows:
        unit = parsed_units.get(row["id"])
        units.append(
            _unit_record(
                db, row, unit, liths[row["id"]], environs[row["id"]], notes, ages
            )
        )

    surfaces = [_boundary_record(db, row) for row in boundaries]

    sections_per_col = defaultdict(set)
    units_per_col = defaultdict(int)
    for row in unit_rows:
        sections_per_col[row["col_id"]].add(row["section_id"])
        units_per_col[row["col_id"]] += 1

    column_records = [
        _column_record(col, units_per_col[col.id], len(sections_per_col[col.id]))
        for col in columns
    ]

    payload = {
        "columns": column_records,
        "units": units,
        "boundaries": surfaces,
    }
    if provisional:
        _renumber(payload)
    return payload


# ------------------------------------------------------------------ queries


def _rows(db, sql: str, **params) -> list[dict]:
    return [dict(r) for r in db.session.execute(text(sql), params).mappings()]


def _fetch_units(db, col_ids):
    if not col_ids:
        return []
    return _rows(
        db,
        """
        SELECT u.id, us.col_id, us.section_id, c.project_id, u.strat_name,
               u.position_bottom, u.position_top, u.min_thick, u.max_thick,
               u.outcrop, u.color, u.orig_id, u.fo, u.lo
        FROM macrostrat.units u
        JOIN macrostrat.units_sections us ON us.unit_id = u.id
        JOIN macrostrat.cols c ON c.id = us.col_id
        WHERE us.col_id = ANY(:col_ids)
        ORDER BY us.col_id, us.section_id, u.position_bottom DESC, u.id
        """,
        col_ids=col_ids,
    )


def _fetch_liths(db, col_ids) -> dict[int, list[dict]]:
    out = defaultdict(list)
    if not col_ids:
        return out
    rows = _rows(
        db,
        """
        SELECT ul.id AS unit_lith_id, ul.unit_id, ul.lith_id, l.lith AS name,
               l.lith_type, l.lith_class, l.lith_color AS color,
               ul.dom, ul.comp_prop, ul.mod_prop,
               COALESCE(array_agg(la.lith_att ORDER BY la.lith_att)
                        FILTER (WHERE la.lith_att IS NOT NULL), '{}') AS atts
        FROM macrostrat.unit_liths ul
        JOIN macrostrat.liths l ON l.id = ul.lith_id
        JOIN macrostrat.units_sections us ON us.unit_id = ul.unit_id
        LEFT JOIN macrostrat.unit_liths_atts ula ON ula.unit_lith_id = ul.id
        LEFT JOIN macrostrat.lith_atts la ON la.id = ula.lith_att_id
        WHERE us.col_id = ANY(:col_ids)
        GROUP BY ul.id, ul.unit_id, ul.lith_id, l.lith, l.lith_type, l.lith_class,
                 l.lith_color, ul.dom, ul.comp_prop, ul.mod_prop
        ORDER BY ul.unit_id, ul.dom DESC, ul.id
        """,
        col_ids=col_ids,
    )
    for row in rows:
        out[row["unit_id"]].append(row)
    return out


def _fetch_environs(db, col_ids) -> dict[int, list[dict]]:
    out = defaultdict(list)
    if not col_ids:
        return out
    rows = _rows(
        db,
        """
        SELECT ue.unit_id, ue.environ_id, e.environ AS name,
               e.environ_type AS type, e.environ_class AS class, e.environ_color AS color
        FROM macrostrat.unit_environs ue
        JOIN macrostrat.environs e ON e.id = ue.environ_id
        JOIN macrostrat.units_sections us ON us.unit_id = ue.unit_id
        WHERE us.col_id = ANY(:col_ids)
        ORDER BY ue.unit_id, ue.id
        """,
        col_ids=col_ids,
    )
    for row in rows:
        out[row["unit_id"]].append(row)
    return out


def _fetch_notes(db, col_ids) -> dict[int, str]:
    if not col_ids:
        return {}
    rows = _rows(
        db,
        """
        SELECT un.unit_id, un.notes
        FROM macrostrat.unit_notes un
        JOIN macrostrat.units_sections us ON us.unit_id = un.unit_id
        WHERE us.col_id = ANY(:col_ids)
        """,
        col_ids=col_ids,
    )
    return {row["unit_id"]: row["notes"] for row in rows}


def _fetch_boundaries(db, col_ids) -> list[dict]:
    if not col_ids:
        return []
    return _rows(
        db,
        """
        SELECT ub.id, s.col_id, ub.section_id, ub.t1, ub.t1_prop, ub.t1_age,
               ub.unit_id, ub.unit_id_2, ub.boundary_status::text AS boundary_status,
               ub.boundary_type::text AS boundary_type, ub.boundary_position, ub.ref_id
        FROM macrostrat.unit_boundaries ub
        JOIN macrostrat.sections s ON s.id = ub.section_id
        WHERE s.col_id = ANY(:col_ids)
        ORDER BY ub.section_id, ub.t1_age, ub.id
        """,
        col_ids=col_ids,
    )


# ------------------------------------------------------------------ records


def _num(value):
    if value is None:
        return None
    return float(value)


def _unit_ages(boundaries: list[dict]) -> dict[int, dict[str, float]]:
    """Each unit's modeled base and top age, from the surfaces it bounds."""
    ages: dict[int, dict[str, float]] = defaultdict(dict)
    for row in boundaries:
        # `unit_id` is the unit below the surface (its top); `unit_id_2` the one above
        if row["unit_id"]:
            ages[row["unit_id"]]["t_age"] = _num(row["t1_age"])
        if row["unit_id_2"]:
            ages[row["unit_id_2"]]["b_age"] = _num(row["t1_age"])
    return ages


def _relative_age(age) -> dict:
    if age is None:
        return {"int_id": None, "int_name": None, "prop": None}
    return {
        "int_id": age.interval.id,
        "int_name": age.interval.name,
        "prop": float(age.proportion),
    }


def _unit_record(db, row, unit, liths, environs, notes, ages) -> dict:
    b = _relative_age(unit.b_age if unit is not None else None)
    t = _relative_age(unit.t_age if unit is not None else None)
    modeled = ages.get(row["id"], {})
    record = {
        "unit_id": row["id"],
        "col_id": row["col_id"],
        "section_id": row["section_id"],
        "project_id": row["project_id"],
        "unit_name": row["strat_name"],
        "strat_name_long": "",
        "strat_name_id": None,
        "Mbr": "",
        "Fm": "",
        "Gp": "",
        "SGp": "",
        "b_pos": _num(row["position_bottom"]),
        "t_pos": _num(row["position_top"]),
        "min_thick": _num(row["min_thick"]),
        "max_thick": _num(row["max_thick"]),
        "outcrop": row["outcrop"],
        "color": row["color"],
        "orig_id": row["orig_id"],
        "notes": notes.get(row["id"], ""),
        "lith": [
            {
                "lith_id": l["lith_id"],
                "name": l["name"],
                "type": l["lith_type"],
                "class": l["lith_class"],
                "color": l["color"],
                "prop": _num(l["comp_prop"]),
                "prop_term": l["dom"] or None,
                "atts": list(l["atts"] or []),
            }
            for l in liths
        ],
        "environ": [
            {
                "environ_id": e["environ_id"],
                "name": e["name"],
                "type": e["type"],
                "class": e["class"],
                "color": e["color"],
            }
            for e in environs
        ],
        "b_int_id": b["int_id"],
        "b_int_name": b["int_name"],
        "b_prop": b["prop"],
        "t_int_id": t["int_id"],
        "t_int_name": t["int_name"],
        "t_prop": t["prop"],
        "b_age": modeled.get("b_age"),
        "t_age": modeled.get("t_age"),
    }
    if unit is not None:
        record["description"] = unit.description
        record["comments"] = unit.comments
        if unit.b_surface_type is not None:
            record["basal_surface"] = unit.b_surface_type.value
    return record


def _boundary_record(db, row) -> dict:
    interval = get_interval_by_id(db, row["t1"])
    return {
        "boundary_id": row["id"],
        "col_id": row["col_id"],
        "section_id": row["section_id"],
        "interval_id": row["t1"],
        "interval_name": interval.name if interval is not None else None,
        "age_bottom": _num(interval.age_bottom) if interval is not None else None,
        "age_top": _num(interval.age_top) if interval is not None else None,
        "rel_position": _num(row["t1_prop"]),
        "model_age": _num(row["t1_age"]),
        "boundary_status": row["boundary_status"],
        "boundary_type": row["boundary_type"] or "",
        "boundary_position": _num(row["boundary_position"]),
        # The v2 API writes 0 for a missing unit, and the editor reads it that way
        "unit_below": row["unit_id"] or 0,
        "unit_above": row["unit_id_2"] or 0,
        "ref_id": row["ref_id"],
    }


def _column_record(col: Column, t_units: int, t_sections: int) -> dict:
    return {
        "col_id": col.id,
        "col_name": col.name,
        "local_id": col.local_id,
        "col_group_id": col.group_id,
        "project_id": col.project_id,
        "status_code": col.status_code,
        "col_type": col.col_type,
        "axis_type": getattr(col, "axis_type", None),
        "lat": col.lat,
        "lng": col.lng,
        "wkt": col.geom or col.rgeom,
        "col_area": None,
        "description": col.description,
        "t_units": t_units,
        "t_sections": t_sections,
        "refs": list(col.ref_ids),
    }


# --------------------------------------------------------------- renumbering


def _renumber(payload: dict) -> None:
    """Replace database ids with negative provisional ones, consistently."""

    def mapping(values):
        ids = sorted({v for v in values if v is not None and v != 0})
        return {old: -(index + 1) for index, old in enumerate(ids)}

    cols = mapping(c["col_id"] for c in payload["columns"])
    units = mapping(u["unit_id"] for u in payload["units"])
    sections = mapping(
        [u["section_id"] for u in payload["units"]]
        + [b["section_id"] for b in payload["boundaries"]]
    )
    boundaries = mapping(b["boundary_id"] for b in payload["boundaries"])

    def remap(table, key, record):
        if record.get(key) in table:
            record[key] = table[record[key]]

    for col in payload["columns"]:
        remap(cols, "col_id", col)
    for unit in payload["units"]:
        remap(units, "unit_id", unit)
        remap(cols, "col_id", unit)
        remap(sections, "section_id", unit)
    for boundary in payload["boundaries"]:
        remap(boundaries, "boundary_id", boundary)
        remap(cols, "col_id", boundary)
        remap(sections, "section_id", boundary)
        remap(units, "unit_below", boundary)
        remap(units, "unit_above", boundary)
