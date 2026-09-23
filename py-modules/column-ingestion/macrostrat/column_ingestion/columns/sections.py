"""A column's sections: the `Section` model, how sections are derived where a source has
none, and their reconciliation ahead of the units that reference them (same transaction,
so `units.section_id`'s foreign key holds — the constraint the legacy importer had to drop).

A section is a conformable, gap-bound package of units. **The norm is one section per
column** — `column.units = [...]` gives exactly that — with the age model computed within
it. Depart from it only when told to: a source that owns its sections builds them,
`Section(orig_id=..., units=...)` (a workbook author's `section_id` counts), and
`split_at_gaps` divides a column at unconformities on explicit request.

**Identity.** `orig_id` is written to `sections.orig_id` and is durable across re-ingest.
Without one, identity is ordinal among the column's unidentified sections, ordered from the
base by unit position on both sides of the match. The two kinds share a column without
interfering: the key function keeps them in separate groups. An unidentified section
inserted below others shifts their ids; units identified by `orig_id` move with them,
positionally keyed units are re-created. The section also scopes a unit's identity — see
`units.writer.unit_identity`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Iterable

from macrostrat.utils import get_logger

from ..boundary_type import NON_CONFORMABLE
from ..database import get_macrostrat_table
from ..intervals import UNMODELED_INTERVAL
from ..reconciliation import ReconciliationPlan, reconcile

if TYPE_CHECKING:
    from ..units.parse import Unit

log = get_logger(__name__)

#: Columns on `sections` the writer owns. `fo_h` / `lo_h` are deliberately absent, as are
#: `units.fo` / `units.lo`: the age model owns these; the section writer only supplies a
#: starting value.
SECTION_COLUMNS = ("fo", "lo")

#: Two positions closer than this are the same surface. Positions are `numeric(7,3)`.
POSITION_TOLERANCE = 1e-6


def _identifier(value) -> str | None:
    """An identifier, or `None` for anything that is not one.

    A CSV-sourced pipeline yields `''` rather than NULL, and an empty string is not an
    identity — treated as one, every unidentified row would collapse onto a single key.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass
class Section:
    """A conformable, gap-bound package of a column's units.

    `orig_id` is the identifier the source — or a workbook author — gave the section, and
    `None` for one we derived; the module docstring says what follows from each. `id` and
    `col_id` are database ids, assigned by `reconcile_sections` along with
    `unit.section_id` on every member unit.
    """

    id: int = -1
    col_id: int = -1
    #: The identifier this section carries in the dataset it came from, written to
    #: `macrostrat.sections.orig_id`. Blank is `None`.
    orig_id: str | None = None
    units: list[Unit] = field(default_factory=list)

    def __post_init__(self):
        self.orig_id = _identifier(self.orig_id)
        internal = internal_unconformities(self)
        if internal:
            # Placeholder for real handling. A section is a conformable package, so a
            # non-conformable surface inside one is a contradiction we currently only
            # report; `split_at_gaps` is the explicit way to divide at it.
            log.warning(
                "Section %s holds %d unit(s) with a non-conformable basal surface above "
                "its base (%s); sections are meant to be conformable packages. Not split "
                "automatically — see split_at_gaps.",
                self.orig_id or "(unidentified)",
                len(internal),
                ", ".join(str(u.name or u.orig_id or "?") for u in internal),
            )


def section_identity(row: dict) -> tuple:
    """Natural key of a section row: its identifier where it has one, else ordinal.

    The leading discriminant keeps the two kinds in one namespace without colliding.
    """
    orig_id = _identifier(row.get("orig_id"))
    if orig_id is not None:
        return ("orig_id", row.get("col_id"), orig_id)
    return ("ordinal", row.get("col_id"))


# --- stratigraphic order ------------------------------------------------------------


def stacking_direction(units: Iterable) -> float:
    """`+1` where positions increase upward (height), `-1` where they increase downward
    (depth), read off the units themselves rather than declared: whichever way the
    majority of units are measured. A column with no measured units reads as height."""
    up = down = 0
    for unit in units:
        if unit.b_pos is None or unit.t_pos is None:
            continue
        if unit.t_pos > unit.b_pos:
            up += 1
        elif unit.t_pos < unit.b_pos:
            down += 1
    return -1.0 if down > up else 1.0


def _base_key(direction: float) -> Callable[[float | None], float]:
    """A sort key placing positions from the base of the column upward; unknown last."""

    def key(position) -> float:
        if position is None:
            return math.inf
        return direction * float(position)

    return key


def _section_base(section: Section, key: Callable) -> float:
    return min((key(u.b_pos) for u in section.units), default=math.inf)


def internal_unconformities(section: Section) -> list:
    """Units above a section's base whose basal surface is non-conformable.

    The lowest positioned unit is exempt — its base is the section's base. Units with
    no position cannot be the base, so a non-conformable one among them counts.
    """
    positioned = [u for u in section.units if u.b_pos is not None]
    lowest = None
    if positioned:
        key = _base_key(stacking_direction(positioned))
        lowest = min(positioned, key=lambda u: key(u.b_pos))
    return [
        u
        for u in section.units
        if u is not lowest and u.b_surface_type in NON_CONFORMABLE
    ]


def _sort_key(value):
    """Order labels numerically where possible, textually otherwise."""
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


def ordered_sections(sections: list[Section]) -> list[Section]:
    """A column's sections from the base upward, which is how the reconciler sees them.

    For an unidentified section this order *is* its identity, so it comes from the rock —
    the base position of its units — rather than from any label. Identified sections are
    ordered the same way for consistency, with `orig_id` breaking ties. Two sections
    sharing an identifier are rejected: the unique index would refuse them anyway, and
    refusing here says which ones.
    """
    identifiers = [s.orig_id for s in sections if s.orig_id is not None]
    duplicates = sorted({k for k in identifiers if identifiers.count(k) > 1})
    if duplicates:
        raise ValueError(f"sections share an identifier: {', '.join(duplicates)}")

    key = _base_key(stacking_direction(u for s in sections for u in s.units))
    return sorted(sections, key=lambda s: (_section_base(s, key), _sort_key(s.orig_id)))


# --- derivation strategies ---------------------------------------------------------


def single_section(units: list[Unit]) -> list[Section]:
    """The whole column as one conformable package — the workbook default when no
    `section_id` is given, and right for any source that asserts continuity."""
    if not units:
        return []
    return [Section(units=list(units))]


def split_at_gaps(
    units: list[Unit], *, tolerance: float = POSITION_TOLERANCE
) -> list[Section]:
    """Divide a column into gap-bound packages, from the base upward.

    A unit opens a new section when its basal boundary is non-conformable
    (`Unit.b_surface_type`), or when its base does not meet the top of the unit below it — a
    break in the position chain is missing rock whether or not the source said so. The
    lowest unit never opens an empty section below itself. Units with no position cannot
    be placed in the chain and are appended to the topmost section.
    """
    if not units:
        return []
    key = _base_key(stacking_direction(units))
    ordered = sorted(units, key=lambda u: key(u.b_pos))

    sections: list[Section] = []
    current: list[Unit] = []
    for unit in ordered:
        if current and _opens_section(current[-1], unit, tolerance):
            sections.append(Section(units=current))
            current = []
        current.append(unit)
    sections.append(Section(units=current))
    return sections


def _opens_section(below: Unit, unit: Unit, tolerance: float) -> bool:
    if unit.b_surface_type in NON_CONFORMABLE:
        return True
    if below.t_pos is None or unit.b_pos is None:
        return False  # a chain we cannot see is not a chain we can call broken
    return abs(float(unit.b_pos) - float(below.t_pos)) > tolerance


# --- writing ----------------------------------------------------------------------


def section_bounds(units: list) -> tuple[int, int]:
    """`(fo, lo)` for a section: its oldest bottom interval and youngest top interval.

    Follows the rule the legacy importer established — `fo` is the interval with the
    greatest `age_bottom` among the section's units, `lo` the one with the least
    `age_top`. Units carrying no interval contribute nothing, and a section with no
    intervals at all gets `UNMODELED_INTERVAL` on both sides: unlike `units`, these
    columns have no foreign key to `intervals`, but using the same sentinel keeps one
    convention rather than two.
    """
    bottoms = [u.b_age.interval for u in units if u.b_age is not None]
    tops = [u.t_age.interval for u in units if u.t_age is not None]
    fo = max(bottoms, key=lambda i: i.age_bottom).id if bottoms else UNMODELED_INTERVAL
    lo = min(tops, key=lambda i: i.age_top).id if tops else UNMODELED_INTERVAL
    return fo, lo


def _existing_sections(db, col_id: int, direction: float) -> list[dict]:
    """A column's existing sections, from the base upward.

    Ordered by the base position of their units — the same rule `ordered_sections`
    applies to ours — rather than by `id`, which only agrees with stratigraphic order if
    the sections happened to be first inserted in that order. Membership comes from
    `units_sections`, as everywhere in the writers.
    """
    rows = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT s.id, s.col_id, s.fo, s.lo, s.orig_id,
                   min(u.position_bottom) AS lowest_base,
                   max(u.position_bottom) AS highest_base
            FROM macrostrat.sections s
            LEFT JOIN macrostrat.units_sections us ON us.section_id = s.id
            LEFT JOIN macrostrat.units u ON u.id = us.unit_id
            WHERE s.col_id = :col_id
            GROUP BY s.id ORDER BY s.id
            """,
            dict(col_id=col_id),
        )
    ]
    key = _base_key(direction)
    for row in rows:
        base = row.pop("lowest_base") if direction > 0 else row.pop("highest_base")
        row.pop("highest_base" if direction > 0 else "lowest_base")
        row["_base"] = key(base)
    rows.sort(key=lambda r: (r["_base"], r["id"]))
    for row in rows:
        row.pop("_base")
    return rows


def reconcile_sections(db, col_id: int, sections: list[Section]) -> ReconciliationPlan:
    """Bring a column's sections in line with `sections`, and stamp ids onto them.

    Sets `section.id` and `section.col_id` on every section, and `unit.section_id` and
    `unit.col_id` on every unit they hold, so callers can go on to write units. The
    column must be complete: an existing section that corresponds to none of `sections`
    is surplus and is deleted, cascading to its units.
    """
    if not sections:
        return ReconciliationPlan()
    sections = ordered_sections(sections)

    desired = []
    for section in sections:
        fo, lo = section_bounds(section.units)
        desired.append(
            {"col_id": col_id, "fo": fo, "lo": lo, "orig_id": section.orig_id}
        )

    direction = stacking_direction(u for s in sections for u in s.units)
    plan, ids = reconcile(
        db,
        get_macrostrat_table(db, "sections"),
        existing=_existing_sections(db, col_id, direction),
        desired=desired,
        key=section_identity,
        owned_columns=SECTION_COLUMNS,
    )

    for section, section_id in zip(sections, ids):
        section.id = section_id
        section.col_id = col_id
        for unit in section.units:
            unit.col_id = col_id
            unit.section_id = section_id

    log.info("sections for col %s: %s", col_id, plan)
    return plan
