"""Reconcile a column's sections, and map the workbook's section labels onto them.

Sections were previously a stub: one per column, with `fo = fo_h = lo = lo_h = -1`
sentinels and a comment that multiple sections were unsupported. Multiple sections per
column is in fact the **normal** case — of the columns in the database, 1,992 have one
section and roughly 1,500 have between two and eight.

Sections are created before the units that reference them, in the same transaction, so
`units.section_id`'s foreign key holds throughout. That is the capability the legacy
importer lacked: unable to precalculate sections, it had to insert units first and drop
the constraint (see `Investigations/Column ingestion architecture.md`).

Identity
--------
`macrostrat.sections` has only `id`, `col_id`, `fo`, `fo_h`, `lo`, `lo_h` — **no column
in which to record the workbook's own section label**. So a section cannot be matched by
an external identifier; it is matched by *ordinal position within its column*. The
reconciler pairs rows positionally inside a key group, so keying on `(col_id,)` alone and
presenting both sides in order does exactly that: existing sections ordered by `id`
against the workbook's sections ordered by label.

The consequence to be aware of: **reordering or inserting sections in the middle of a
workbook remaps the ones after it.** Units move with them, so nothing is corrupted, but
ids shift. Giving `sections` a column to carry the workbook label would fix it properly
and is the obvious remedy if this becomes a real problem.
"""

from macrostrat.utils import get_logger

from ..database import get_macrostrat_table
from ..intervals import UNMODELED_INTERVAL
from ..reconciliation import ReconciliationPlan, reconcile

log = get_logger(__name__)

#: The age model owns these; the section writer only supplies a starting value.
SECTION_COLUMNS = ("fo", "lo")


def group_units_by_section(units: list) -> dict:
    """Group units by their workbook section label, preserving a stable order.

    Labels are sorted so the mapping onto existing sections is deterministic. A workbook
    that omits `section_id` entirely leaves every unit with the same label, which
    collapses to a single section.
    """
    groups: dict = {}
    for unit in units:
        groups.setdefault(unit.section_key, []).append(unit)
    return {key: groups[key] for key in sorted(groups, key=_sort_key)}


def _sort_key(value):
    """Order section labels numerically where possible, textually otherwise."""
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


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


def reconcile_sections(db, col_id: int, units: list) -> tuple[dict, ReconciliationPlan]:
    """Bring a column's sections in line with the workbook, and map labels to ids.

    Returns `({section_key: sections.id}, plan)`. Callers assign `unit.section_id` from
    the mapping before writing units.
    """
    groups = group_units_by_section(units)
    if not groups:
        return {}, ReconciliationPlan()

    desired = []
    for section_units in groups.values():
        fo, lo = section_bounds(section_units)
        desired.append({"col_id": col_id, "fo": fo, "lo": lo})

    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, col_id, fo, lo FROM macrostrat.sections
            WHERE col_id = :col_id ORDER BY id
            """,
            dict(col_id=col_id),
        )
    ]

    plan, ids = reconcile(
        db,
        get_macrostrat_table(db, "sections"),
        existing=existing,
        desired=desired,
        # Ordinal identity: pairing happens positionally inside the single col_id group.
        key=("col_id",),
        owned_columns=SECTION_COLUMNS,
    )

    mapping = dict(zip(groups, ids))
    log.info("sections for col %s: %s -> %s", col_id, plan, mapping)
    return mapping, plan


def assign_section_ids(db, col_id: int, units: list) -> dict:
    """Reconcile a column's sections and stamp the resulting ids onto its units."""
    mapping, _ = reconcile_sections(db, col_id, units)
    for unit in units:
        unit.col_id = col_id
        unit.section_id = mapping[unit.section_key]
    return mapping
