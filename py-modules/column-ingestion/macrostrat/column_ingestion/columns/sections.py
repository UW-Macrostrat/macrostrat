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
`macrostrat.sections` now carries `orig_id`, so a section **can** be matched by an
external identifier — when the source has one. Two regimes, and which applies depends on
the dataset rather than on a setting:

- **`Unit.section_orig_id` set** — the source has sections as real objects. Sections key
  on `(col_id, orig_id)`, and their ids are durable across re-ingest.
- **Not set** — our sections are our own construction (GBDB's gap-bound packages are
  derived, so GBDB has no identifier for them). Identity falls back to *ordinal position
  within the column*: the reconciler pairs rows positionally inside a key group, so
  keying on `(col_id,)` and presenting both sides in order matches existing sections
  ordered by `id` against ours ordered by label.

The consequence of the ordinal regime, unchanged: **inserting a section mid-column remaps
the ones after it.** Nothing is corrupted — units move with them, and `units.section_id`
is an owned column rather than part of a unit's key precisely so that this is absorbed —
but ids shift, and a shifted id means a section id held elsewhere now names different
rock. Supplying `section_orig_id` is what removes that hazard.
"""

from macrostrat.utils import get_logger

from ..database import get_macrostrat_table
from ..intervals import UNMODELED_INTERVAL
from ..reconciliation import ReconciliationPlan, reconcile

log = get_logger(__name__)

#: The age model owns these; the section writer only supplies a starting value.
SECTION_COLUMNS = ("fo", "lo")

#: Ordinal identity, for sections the source does not identify: pairing happens
#: positionally inside the single `col_id` group.
SECTION_ORDINAL_KEY = ("col_id",)


def section_identity(row: dict) -> tuple:
    """Natural key of a section: its source identifier where it has one, else ordinal.

    The leading discriminant keeps the two regimes from colliding, but note that unlike
    the column and unit keys these two are **not** freely mixable within one column: the
    ordinal branch is positional, so a column holding both identified and unidentified
    sections would pair the unidentified ones against whatever ordinal slots are left.
    That does not arise in practice, because whether a source identifies its sections is
    a property of the dataset, not of the individual section.
    """
    orig_id = row.get("orig_id")
    if orig_id is not None and str(orig_id).strip() != "":
        return ("orig_id", row.get("col_id"), str(orig_id).strip())
    return ("ordinal", row.get("col_id"))


def _identifier(value) -> str | None:
    """An identifier, or `None` for anything that is not one (including `''`)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def section_grouping_key(unit):
    """What a unit is grouped into a section by.

    The source's own section identifier where there is one, and the caller's
    `section_key` otherwise. One value drives both the grouping and the resulting
    section's identity, which is the whole distinction: **a source that identifies its
    sections is telling us how to divide the column, not just what to call the pieces.**
    Deriving sections ourselves — GBDB splits on non-conformable contacts — is what
    happens when the source says nothing.

    Keeping these as one value rather than two is not a detail. Grouping by one attribute
    while taking identity from another lets the two disagree, and a source-identified
    section would then be assembled from the wrong units.
    """
    orig_id = getattr(unit, "section_orig_id", None)
    if orig_id is not None and str(orig_id).strip() != "":
        return str(orig_id).strip()
    return unit.section_key


def group_units_by_section(units: list) -> dict:
    """Group units into sections, preserving a stable order.

    Keys are sorted so the mapping onto existing sections is deterministic. A caller that
    supplies neither a source identifier nor a `section_key` leaves every unit with the
    same key, which collapses to a single section.
    """
    groups: dict = {}
    for unit in units:
        groups.setdefault(section_grouping_key(unit), []).append(unit)
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
        # A group's units agree on their source identifier by construction — it is what
        # they were grouped by. `None` leaves the section on ordinal identity.
        orig_id = _identifier(getattr(section_units[0], "section_orig_id", None))
        desired.append({"col_id": col_id, "fo": fo, "lo": lo, "orig_id": orig_id})

    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, col_id, fo, lo, orig_id FROM macrostrat.sections
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
        key=section_identity,
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
        unit.section_id = mapping[section_grouping_key(unit)]
    return mapping
