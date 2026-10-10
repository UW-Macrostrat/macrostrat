"""Data-quality checks over a parsed dataset, reported as notices.

These run after parsing and before anything is written, on the `Column` and `Unit`
objects rather than on the sheets, so the same checks apply to a workbook and to a
column submitted from an editor. The parsers report what they could not read; this
module reports what reads fine but does not hold together as a column.
"""

from __future__ import annotations

from . import notices
from .columns.parse import Column
from .units.parse import Unit


def validate_dataset(columns: list[Column]) -> None:
    for col in columns:
        with notices.notice_context(col_id=col.local_id):
            validate_column(col)


def validate_column(col: Column) -> None:
    label = col.name or col.local_id or "column"
    units = col.units

    _check_location(col, label)

    if len(units) == 0:
        notices.warning("no-units", f"{label}: no units")
        return

    for unit in units:
        with notices.notice_context(unit=unit.name):
            _check_unit_ages(unit)

    _check_age_model(col, label, units)
    _check_age_order(col, units)


def _check_location(col: Column, label: str) -> None:
    has_point = col.lat is not None and col.lng is not None
    has_polygon = bool(col.geom and str(col.geom).strip()) or bool(
        col.rgeom and str(col.rgeom).strip()
    )
    if not has_point and not has_polygon:
        notices.error(
            "no-location",
            f"{label}: no location — give `lat`/`lng` or a polygon in `geom`",
            column="lat",
        )
        return
    is_line = (
        str(col.geom or "")
        .strip()
        .upper()
        .startswith(("LINESTRING", "MULTILINESTRING"))
    )
    if col.col_type == "section" and not has_point and not is_line:
        # A measured section is a place, not a region; a polygon alone is a hint
        notices.warning(
            "no-specific-location",
            f"{label}: a measured section needs a point location, not just a polygon",
            column="lat",
        )
    if has_point and (abs(col.lat) > 90 or abs(col.lng) > 180):
        notices.error(
            "location-out-of-range",
            f"{label}: lat/lng ({col.lat}, {col.lng}) is not a coordinate",
            column="lat",
        )


def _check_unit_ages(unit: Unit) -> None:
    if unit.b_age is None or unit.t_age is None:
        return
    base, top = float(unit.b_age.model_age()), float(unit.t_age.model_age())
    if base < top:
        notices.error(
            "contradictory-age-constraints",
            f"base ({unit.b_age.interval.name}, {base:g} Ma) is younger than "
            f"top ({unit.t_age.interval.name}, {top:g} Ma)",
            column="b_int",
            detail={"b_age": base, "t_age": top},
        )


def _constrained_positions(units: list[Unit]) -> set[float]:
    positions = set()
    for unit in units:
        if unit.b_age is not None and unit.b_pos is not None:
            positions.add(float(unit.b_pos))
        if unit.t_age is not None and unit.t_pos is not None:
            positions.add(float(unit.t_pos))
    return positions


def _check_age_model(col: Column, label: str, units: list[Unit]) -> None:
    constrained = _constrained_positions(units)
    if len(constrained) >= 2:
        return
    # A composite column is placed in time by its age model; a measured section can
    # stand on its positions alone, but its ages then cannot be modeled.
    report = notices.error if col.col_type == "column" else notices.warning
    if len(constrained) == 0:
        report(
            "no-age-model",
            f"{label}: no age constraints — no unit names an interval, so no age "
            "model can be built",
            column="b_int",
        )
    else:
        report(
            "insufficient-age-constraints",
            f"{label}: only one surface is constrained in time; an age model needs "
            "at least two",
            column="b_int",
        )


def _check_age_order(col: Column, units: list[Unit]) -> None:
    """Ages should get younger upward through the column."""
    placed = [u for u in units if u.b_pos is not None and u.t_pos is not None]
    if len(placed) < 2:
        return
    # Height and ordinal positions grow upward; depth grows downward
    upward = 1.0
    if getattr(col, "axis_type", None) == "depth":
        upward = -1.0
    ordered = sorted(placed, key=lambda u: upward * float(u.b_pos))

    last_age, last_unit = None, None
    for unit in ordered:
        for age, side in ((unit.b_age, "base"), (unit.t_age, "top")):
            if age is None:
                continue
            model_age = float(age.model_age())
            if last_age is not None and model_age > last_age + 1e-6:
                notices.warning(
                    "age-inversion",
                    f"{unit.name or 'unit'} {side} ({age.interval.name}, {model_age:g} Ma) "
                    f"is older than the constraint below it in "
                    f"{last_unit.name or 'the unit below'} ({last_age:g} Ma)",
                    unit=unit.name,
                    column="b_int" if side == "base" else "t_int",
                )
            last_age, last_unit = model_age, unit
