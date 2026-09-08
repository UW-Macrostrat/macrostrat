"""Write a section's units and their dependents, reconciling rather than replacing.

The previous writer deleted every unit for a (column, section) and re-inserted. That
is fine for a genuinely new column and wrong on re-import, because `unit_liths`,
`unit_liths_atts`, `unit_environs`, `unit_notes`, `unit_strat_names` and
`unit_boundaries` all reference `units.id` with `ON DELETE CASCADE` — so a rebuild
silently destroyed the age model built from the same workbook.

Everything here matches on a declared natural key instead, via
`reconciliation.plan_reconciliation`. Because units are no longer deleted, the
dependent tables are no longer cleaned up by the cascade either, so each of them is
reconciled explicitly.

Natural keys
------------

| table | key |
| --- | --- |
| `units` | `(col_id, section scope, orig_id)`, or `(col_id, section scope, strat_name, position_bottom, position_top)` |
| `units_sections` | `(unit_id, col_id, section_id)` |
| `unit_liths` | `(unit_id, lith_id, dom)` |
| `unit_liths_atts` | `(unit_lith_id, lith_att_id)` |

The unit key deliberately **excludes `fo`/`lo`**, which the legacy importer included.
Those are computed outputs now (see `age_model`), so they cannot also identify a row.

`macrostrat.units.orig_id` — the identifier a unit carries in the dataset it came from —
is preferred over position, because position cannot survive re-ingest: it is derived from
thickness, so an upstream correction reads as a different unit, and the row is deleted and
re-inserted, cascading away its `unit_liths`, `unit_liths_atts`, `unit_environs`,
`unit_notes`, `unit_strat_names` and `unit_boundaries`. Avoiding that churn is the whole
purpose here; see `unit_identity` for the one rule.

`section_id` is owned rather than keyed whenever the source does not identify its
sections, so a section renumbering is absorbed instead of replacing every unit. Nothing
downstream needs section ids to be stable: `unit_boundaries` identity is the pair of units
a surface separates (`age_model.reconciliation._identity`).

`section_id` and `strat_name` are never NULL or empty in `macrostrat.units`.
"""

from collections import defaultdict

from macrostrat.utils import get_logger

from ..database import get_macrostrat_table
from ..intervals import UNMODELED_INTERVAL
from ..reconciliation import ReconciliationPlan, reconcile
from .parse import Unit

log = get_logger(__name__)

#: The **fallback** key, for units carrying no `orig_id`: unchanged from before
#: `orig_id` existed, `section_id` included. Widening it to the column was measured and
#: rejected — dropping `section_id` takes colliding groups in `macrostrat.units` from 34
#: (93 rows) to 696 (1,956 rows), because 842 columns restart `position_bottom` /
#: `position_top` per section rather than measuring them continuously up the column.
UNIT_KEY_COLUMNS = (
    "col_id",
    "section_id",
    "strat_name",
    "position_bottom",
    "position_top",
)

#: Columns on `units` this writer owns and may overwrite on a matched row.
#:
#: `fo`/`lo` are deliberately **absent**. For the eODP columns those fields *are* the
#: age control (see `age_model.eodp`), so a generic re-import must never overwrite them
#: — this writer cannot tell whether it is looking at such a column. They are still
#: supplied on INSERT, because they are NOT NULL and a new row has to carry something;
#: see `_desired_unit_row` for the caveat on where that value comes from.
#: `section_id` is here as well as in `UNIT_KEY_COLUMNS`, which looks contradictory and
#: is not. A unit matched by `orig_id` may have moved to a different section, and the new
#: `section_id` has to be written. A unit matched by the fallback key cannot have moved,
#: because `section_id` is part of that key — so for those rows the update is a provable
#: no-op. Keeping one `owned_columns` tuple for both paths is simpler than splitting the
#: reconcile in two.
UNIT_COLUMNS = ("section_id", "max_thick", "min_thick", "outcrop", "color")

_POSITION_SCALE = 3  # numeric(7,3)
_THICKNESS_SCALE = 2  # numeric(7,2)
UNIT_SCALES = {"max_thick": _THICKNESS_SCALE, "min_thick": _THICKNESS_SCALE}


def _round(value, scale: int):
    return None if value is None else round(float(value), scale)


#: How each key column is normalised before comparison. Positions are quantized
#: because they are `numeric(7,3)` in the database and part of the key.
_KEY_NORMALIZERS = {
    "strat_name": lambda v: (v or "").strip(),
    "position_bottom": lambda v: _round(v, _POSITION_SCALE),
    "position_top": lambda v: _round(v, _POSITION_SCALE),
}


def _identifier(value) -> str | None:
    """An identifier, or `None` for anything that is not one.

    A CSV-sourced pipeline yields `''` rather than NULL, and an empty string is not an
    identity — if it were treated as one, every unidentified row would collapse onto a
    single key.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def unit_identity(row: dict) -> tuple:
    """Natural key of a unit: the source's identifier, in the scope the source declares.

    Two substitutions rather than a hierarchy of cases.

    **Scope** is the section when the source names its sections, and the column when it
    does not. A source that gives its sections identifiers has thereby declared them the
    context its unit identifiers resolve in; where it does not, our sections are our own
    construction (GBDB's gap-bound packages are derived) and a unit may move between them
    as an artifact, so they must not participate in identity.

    **Identifier** is the unit's `orig_id` where it has one, and its position where it
    does not. Position needs a scope even when that scope is only our own `section_id`,
    because 842 columns restart `position_bottom` / `position_top` per section.

    The two shapes differ in arity, and the leading tag keeps them disjoint regardless.
    """
    scope = _identifier(row.get("section_orig_id"))
    unit_orig_id = _identifier(row.get("orig_id"))

    if unit_orig_id is not None:
        return ("orig_id", row.get("col_id"), scope, unit_orig_id)

    return (
        "position",
        row.get("col_id"),
        scope if scope is not None else row.get("section_id"),
    ) + tuple(
        _KEY_NORMALIZERS.get(c, lambda v: v)(row.get(c))
        for c in ("strat_name", "position_bottom", "position_top")
    )


def _desired_unit_row(unit: Unit) -> dict:
    thickness = (
        abs(float(unit.t_pos) - float(unit.b_pos))
        if unit.t_pos is not None and unit.b_pos is not None
        else None
    )
    row = {
        "col_id": unit.col_id,
        "section_id": unit.section_id,
        "strat_name": unit.name or "default",
        "position_bottom": unit.b_pos,
        "position_top": unit.t_pos,
        "orig_id": unit.orig_id,
        "max_thick": thickness,
        "min_thick": thickness,
        "outcrop": "surface",
        "color": "",
    }
    # INSERT-only. Ingesting the physical column is deliberately decoupled from age
    # modeling, which usually needs review, so there may be no ages at all yet — and a
    # unit carrying no interval assignment is normal for high-resolution continuous
    # stratigraphy. `fo`/`lo` are NOT NULL, so a new row takes the unit's own interval
    # where the workbook happens to supply one and `UNMODELED_INTERVAL` otherwise.
    # Neither is an age claim; writing the age model replaces both.
    row["fo"] = unit.b_age.interval.id if unit.b_age is not None else UNMODELED_INTERVAL
    row["lo"] = unit.t_age.interval.id if unit.t_age is not None else UNMODELED_INTERVAL
    return row


def _fetch(db, sql: str, params: dict) -> list[dict]:
    return [dict(row._mapping) for row in db.run_query(sql, params)]


def _existing_units(db, col_id: int) -> list[dict]:
    """A **column's** existing units, with membership taken from `units_sections`.

    Neither `units.col_id` nor `units.section_id` is authoritative — see
    `age_model.eodp.eodp_units`. Reading them here would scope the reconciliation to the
    wrong set of units, and the natural key would then compare against a `col_id` the
    section itself does not agree with.

    Scoped to the column rather than to one section, which the `orig_id` key requires: a
    unit that moved between sections is not in its new section's existing set, so a
    section-scoped fetch would see it as new and delete the original — the section-remap
    cascade this writer exists to avoid. Fallback-keyed rows are unaffected by the wider
    scope because `section_id` is part of their key, so it still discriminates them.
    """
    return _fetch(
        db,
        """
        SELECT u.id, us.col_id, us.section_id, u.strat_name, u.orig_id,
               u.position_bottom, u.position_top,
               u.max_thick, u.min_thick, u.outcrop, u.color, u.fo, u.lo
        FROM macrostrat.units u
        JOIN macrostrat.units_sections us ON us.unit_id = u.id
        WHERE us.col_id = :col_id
        ORDER BY u.id
        """,
        dict(col_id=col_id),
    )


def reconcile_units(db, units: list[Unit]) -> ReconciliationPlan:
    """Bring `macrostrat.units` in line with `units` for one whole column.

    Sets `unit.id` on every unit — matched or inserted — so callers can go on to write
    dependent rows and build an age model.

    Takes a column at a time rather than a `(column, section)` pair, so that a unit which
    changed sections is matched rather than replaced. The caller must therefore pass
    **every** unit the column should end up with: a unit present in the database and
    absent from `units` is surplus and is deleted, which is the point of reconciling, but
    it means a partial set silently prunes the remainder.
    """
    if not units:
        return ReconciliationPlan()

    col_ids = {u.col_id for u in units}
    if len(col_ids) != 1:
        raise ValueError(
            f"reconcile_units handles one col_id at a time; got {sorted(col_ids)}"
        )
    col_id = col_ids.pop()

    desired = [_desired_unit_row(u) for u in units]

    # `section_orig_id` is a key component but not a column on `macrostrat.units`, so it
    # cannot ride on the desired rows — those are inserted verbatim. Both sides resolve it
    # through this map, which keeps `unit_identity` a plain function of a row.
    section_orig_ids = {
        u.section_id: u.section_orig_id for u in units if u.section_orig_id is not None
    }

    def key(row: dict) -> tuple:
        return unit_identity(
            {**row, "section_orig_id": section_orig_ids.get(row.get("section_id"))}
        )

    plan, ids = reconcile(
        db,
        get_macrostrat_table(db, "units"),
        existing=_existing_units(db, col_id),
        desired=desired,
        key=key,
        owned_columns=UNIT_COLUMNS,
        scales=UNIT_SCALES,
    )
    for unit, unit_id in zip(units, ids):
        unit.id = unit_id

    log.info("units for col %s: %s", col_id, plan)
    return plan


def reconcile_units_sections(db, units: list[Unit]) -> ReconciliationPlan:
    """Reconcile the `units_sections` join rows for a set of units."""
    if not units:
        return ReconciliationPlan()

    existing = _fetch(
        db,
        """
        SELECT id, unit_id, col_id, section_id FROM macrostrat.units_sections
        WHERE unit_id = ANY(:unit_ids) ORDER BY id
        """,
        dict(unit_ids=[u.id for u in units]),
    )
    plan, _ = reconcile(
        db,
        get_macrostrat_table(db, "units_sections"),
        existing=existing,
        desired=[
            {"unit_id": u.id, "col_id": u.col_id, "section_id": u.section_id}
            for u in units
        ],
        key=("unit_id", "col_id", "section_id"),
        owned_columns=(),  # a pure join row: presence is the whole content
    )
    log.info("units_sections: %s", plan)
    return plan


LITH_COLUMNS = ("prop", "comp_prop", "mod_prop", "toc", "ref_id")


def reconcile_unit_liths(db, units: list[Unit]) -> ReconciliationPlan:
    """Reconcile `unit_liths` and `unit_liths_atts` for a set of units.

    Previously these were re-inserted wholesale after the parent units were deleted;
    with units preserved they would accumulate duplicates instead.
    """
    if not units:
        return ReconciliationPlan()

    desired = []
    attributes: list[set[int]] = []
    for unit in units:
        n_liths = len(unit.lithology)
        for lith in unit.lithology:
            dom = lith.dom.value if lith.dom is not None else ""
            desired.append(
                {
                    "unit_id": unit.id,
                    "lith_id": lith.id,
                    "dom": dom,
                    # TODO: dom and prop are equivalent for now
                    "prop": dom,
                    "comp_prop": 1 / n_liths,
                    "mod_prop": 1 / n_liths,
                    "toc": 0.0,
                    "ref_id": 0,
                }
            )
            attributes.append({att.id for att in (lith.attributes or set())})

    existing = _fetch(
        db,
        """
        SELECT id, unit_id, lith_id, dom, prop, comp_prop, mod_prop, toc, ref_id
        FROM macrostrat.unit_liths
        WHERE unit_id = ANY(:unit_ids) ORDER BY id
        """,
        dict(unit_ids=[u.id for u in units]),
    )
    plan, unit_lith_ids = reconcile(
        db,
        get_macrostrat_table(db, "unit_liths"),
        existing=existing,
        desired=desired,
        key=("unit_id", "lith_id", "dom"),
        owned_columns=LITH_COLUMNS,
        scales={"comp_prop": 4, "mod_prop": 4, "toc": 4},
    )

    _reconcile_lith_atts(db, unit_lith_ids, attributes)
    log.info("unit_liths: %s", plan)
    return plan


def _reconcile_lith_atts(
    db, unit_lith_ids: list[int], attributes: list[set[int]]
) -> None:
    """Reconcile `unit_liths_atts` for each `unit_liths` row, by position."""
    if not unit_lith_ids:
        return
    existing = _fetch(
        db,
        """
        SELECT id, unit_lith_id, lith_att_id, ref_id FROM macrostrat.unit_liths_atts
        WHERE unit_lith_id = ANY(:ids) ORDER BY id
        """,
        dict(ids=unit_lith_ids),
    )
    desired = [
        {"unit_lith_id": unit_lith_id, "lith_att_id": att_id, "ref_id": 0}
        for unit_lith_id, att_ids in zip(unit_lith_ids, attributes)
        for att_id in sorted(att_ids)
    ]
    plan, _ = reconcile(
        db,
        get_macrostrat_table(db, "unit_liths_atts"),
        existing=existing,
        desired=desired,
        key=("unit_lith_id", "lith_att_id"),
        owned_columns=("ref_id",),
    )
    log.info("unit_liths_atts: %s", plan)


#: Nothing on `unit_environs` is ours to update: `f`, `l` and `date_mod` are nullable, and
#: `ref_id` is set on INSERT only so a curated reference survives a re-import.
ENVIRON_COLUMNS = ()


def reconcile_unit_environs(db, units: list[Unit]) -> ReconciliationPlan:
    """Reconcile `unit_environs` for a set of units.

    The `unit_liths` shape, minus the attributes — an environment is one token resolving
    to one `environs` row, so there is no second level to reconcile.
    """
    if not units:
        return ReconciliationPlan()

    existing = _fetch(
        db,
        """
        SELECT id, unit_id, environ_id FROM macrostrat.unit_environs
        WHERE unit_id = ANY(:unit_ids) ORDER BY id
        """,
        dict(unit_ids=[u.id for u in units]),
    )
    desired = [
        # `ref_id` is passed explicitly as NULL rather than left to the column default.
        # That default is `1`, which is a real reference in production but not in a fresh
        # database, so relying on it makes the insert fail against the FK to `refs`. NULL
        # means "no reference recorded" and is already what 23,672 existing rows use.
        {"unit_id": unit.id, "environ_id": environ.id, "ref_id": None}
        for unit in units
        for environ in sorted(unit.environment, key=lambda e: e.id)
    ]
    plan, _ = reconcile(
        db,
        get_macrostrat_table(db, "unit_environs"),
        existing=existing,
        desired=desired,
        key=("unit_id", "environ_id"),
        owned_columns=ENVIRON_COLUMNS,
    )
    log.info("unit_environs: %s", plan)
    return plan


def compose_note(description: str | None, comments: str | None) -> str | None:
    """One note per unit, composed from the two free-text fields.

    Following the legacy contract: whichever is present, or both joined with `"; "`.
    Returns `None` when there is nothing to say, in which case no row is written.
    """
    parts = [p.strip() for p in (description, comments) if p and str(p).strip()]
    return "; ".join(parts) or None


def reconcile_unit_notes(db, units: list[Unit]) -> ReconciliationPlan:
    """Reconcile `unit_notes`, at most one row per unit.

    Unlike the other dependents the note *text* is the payload rather than part of the
    key, so an edited description updates the existing row in place instead of replacing
    it — and a unit whose text is cleared has its note removed.
    """
    if not units:
        return ReconciliationPlan()

    existing = _fetch(
        db,
        """
        SELECT id, unit_id, notes FROM macrostrat.unit_notes
        WHERE unit_id = ANY(:unit_ids) ORDER BY id
        """,
        dict(unit_ids=[u.id for u in units]),
    )
    desired = []
    for unit in units:
        notes = compose_note(unit.description, unit.comments)
        if notes is not None:
            desired.append({"unit_id": unit.id, "notes": notes})

    plan, _ = reconcile(
        db,
        get_macrostrat_table(db, "unit_notes"),
        existing=existing,
        desired=desired,
        key=("unit_id",),
        owned_columns=("notes",),
    )
    log.info("unit_notes: %s", plan)
    return plan


def write_units(db, units: list[Unit]) -> list[Unit]:
    """Reconcile a set of units and their dependent rows.

    Units are reconciled per column, which is the scope of the `orig_id` key — see
    `reconcile_units` — so a unit that moved between sections of its column is matched
    rather than replaced. The dependent tables are keyed on `unit_id` and so are handled
    across the whole set at once.

    Returns the units with `id` set.
    """
    if not units:
        return units

    by_column: dict[int, list[Unit]] = defaultdict(list)
    for unit in units:
        by_column[unit.col_id].append(unit)
    for column_units in by_column.values():
        reconcile_units(db, column_units)

    reconcile_units_sections(db, units)
    reconcile_unit_liths(db, units)
    reconcile_unit_environs(db, units)
    reconcile_unit_notes(db, units)
    return units
