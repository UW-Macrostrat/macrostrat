"""Reconcile a rebuilt age model against the `unit_boundaries` rows already stored.

Rebuilding an age model used to mean deleting a section's boundaries and inserting
fresh ones, which burned one id per boundary on every run (~78,000 for eODP alone)
and gave every surface a new identity. Instead we match rebuilt boundaries onto the
existing rows by their **natural key — the pair of units a boundary separates** —
so a surface that has not moved keeps its `id`.

`plan_boundary_reconciliation` is pure: plain dicts in, a `BoundaryPlan` out, so the
matching rules are testable without a database. `reconcile_unit_boundaries` wraps it
with the IO.

TODO — replace most of this with a database constraint
------------------------------------------------------
The planner exists largely because the table cannot yet express its own key. Once it
can, this collapses to an upsert plus a single delete:

```sql
ALTER TABLE macrostrat.unit_boundaries
  ADD CONSTRAINT unit_boundaries_section_units_key
  UNIQUE NULLS NOT DISTINCT (section_id, unit_id, unit_id_2);

INSERT INTO macrostrat.unit_boundaries (…)
VALUES (…)
ON CONFLICT (section_id, unit_id, unit_id_2) DO UPDATE
   SET t1 = EXCLUDED.t1, t1_prop = EXCLUDED.t1_prop, …;

DELETE FROM macrostrat.unit_boundaries
 WHERE section_id = :section_id AND id <> ALL(:touched);
```

`NULLS NOT DISTINCT` (PostgreSQL 15+) is what makes `ON CONFLICT` inference work with
the NULL sentinels. Two things block it today, and until they are cleared this module
is what enforces the key:

1. **The key is not unique yet** — 294 colliding groups. 255 are exact-duplicate
   rows (mechanical to clean), but 39 have genuinely differing payloads and need a
   rule: 22 in project 1, 16 in eODP, 1 in project 8. The constraint cannot be added
   provisionally either: `UNIQUE … NOT VALID` is rejected outright
   (`UNIQUE constraints cannot be marked NOT VALID`) — `NOT VALID` exists only for
   `CHECK` and `FOREIGN KEY`.
2. **The two "no unit" sentinels are still mixed** — see `no_unit`. A `0` row does
   not conflict with a `NULL` row even under `NULLS NOT DISTINCT`, so an upsert would
   insert a duplicate for every legacy top and basal boundary instead of matching it.

Note also that an upsert would not fully solve the id-space concern on its own: it
burns a sequence value per *attempted* insert even when the row conflicts, whereas
the `UPDATE` path here burns none.

Even once the constraint lands, the quantized change detection below is worth
keeping — it is what makes a rebuild a genuine no-op rather than a silent rewrite.
"""

from typing import TYPE_CHECKING

from macrostrat.utils import get_logger

from ..database import get_macrostrat_table
from ..reconciliation import ReconciliationPlan, plan_reconciliation, reconcile

if TYPE_CHECKING:
    from .model import UnitBoundary

log = get_logger(__name__)


def write_unit_boundaries(db, unit_boundaries: list["UnitBoundary"]):
    write_unit_boundaries_from_mappings(db, [u.to_dict() for u in unit_boundaries])


def write_unit_boundaries_from_mappings(db, mappings: list[dict]):
    if not hasattr(db.model, "macrostrat_unit_boundaries"):
        db.automap(schemas=["macrostrat"])
    db.session.bulk_insert_mappings(db.model.macrostrat_unit_boundaries, mappings)


# Columns the age model owns and may overwrite on an existing boundary row.
# Everything else is left alone — notably `unit_id` / `unit_id_2`, so a matched
# legacy row keeps its `0` sentinel (see `no_unit`), and the derived/curated
# columns `paleo_lat`, `paleo_lng`, `boundary_type` and `ref_id`. Leaving those
# untouched is a side benefit; the point of matching rather than recreating is to
# keep boundary ids stable instead of consuming the id space on every rebuild.
AGE_MODEL_COLUMNS = (
    "t1",
    "t1_prop",
    "t1_age",
    "boundary_status",
    "boundary_position",
)

# Numeric scales of the target columns, so a rebuilt value is compared against
# the database at the precision the database actually stores. Without this every
# row looks changed on every run and identity is preserved in name only.
_COLUMN_SCALE = {"t1_prop": 5, "t1_age": 4, "boundary_position": 3}


def no_unit(value) -> bool:
    """Whether a `unit_id` / `unit_id_2` means "there is no unit on this side".

    Two conventions are in the table and both are valid. Legacy rows — the bulk,
    ~12,450 of them — use `0`; newer rows use `NULL`, which is what we now write.
    A wholesale migration to `NULL` has been deliberately deferred, so any code
    reading these columns has to accept both.
    """
    return value is None or value == 0


def _identity(row: dict) -> tuple:
    """The natural key of a boundary: the pair of units it separates.

    Normalises the two "no unit" conventions together, so a legacy `0` row and the
    `NULL` we would write for the same surface match rather than being treated as
    two different boundaries. Without this, a rebuild replaces every top and basal
    boundary in the section and burns an id for each.

    Note `unit_id` / `unit_id_2` are deliberately absent from `AGE_MODEL_COLUMNS`:
    a matched legacy row therefore keeps its `0`, and only newly inserted rows get
    `NULL`. Mixing the two in one table is intentional pending that migration; no
    section currently holds both conventions for the same surface.

    This key is *not* unique in the database yet — 294 groups collide, 255 of them
    exact-duplicate rows. Duplicates within a group are matched positionally and
    any surplus is deleted, which incidentally cleans them up. A real
    `UNIQUE NULLS NOT DISTINCT (section_id, unit_id, unit_id_2)` plus an upsert
    would replace most of this planner, but it cannot be added until those
    duplicates are resolved *and* the sentinels are unified — Postgres has no
    `NOT VALID` for unique constraints, and a `0` row does not conflict with a
    `NULL` one.
    """

    def unit(value):
        return None if no_unit(value) else int(value)

    return (unit(row.get("unit_id")), unit(row.get("unit_id_2")))


#: Legacy alias — the plan shape is now shared across entities.
BoundaryPlan = ReconciliationPlan


def plan_boundary_reconciliation(
    existing: list[dict], desired: list[dict]
) -> ReconciliationPlan:
    """Match rebuilt boundaries onto existing rows, preserving row identity.

    Pure: takes and returns plain dicts so it can be tested without a database.
    `existing` rows must carry `id` plus the age-model columns; `desired` rows are
    `UnitBoundary.to_dict()` output.

    A surface that still separates the same two units keeps its `id`, and is only
    updated if one of the age-model columns actually moved.
    """
    return plan_reconciliation(
        existing,
        desired,
        key=_identity,
        owned_columns=AGE_MODEL_COLUMNS,
        scales=_COLUMN_SCALE,
    )


def reconcile_unit_boundaries(
    db, section_id: int, boundaries: list["UnitBoundary"], *, dry_run: bool = False
) -> ReconciliationPlan:
    """Bring a section's `unit_boundaries` in line with a rebuilt age model.

    Replaces the older delete-everything-then-insert flow: unchanged surfaces keep their
    `id` (which API v2 exposes as `boundary_id`) and their curated columns. Returns the
    plan, which is also what `dry_run=True` produces without writing.
    """
    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, unit_id, unit_id_2, t1, t1_prop, t1_age,
                   boundary_status, boundary_position
            FROM macrostrat.unit_boundaries
            WHERE section_id = :section_id
            ORDER BY id
            """,
            dict(section_id=section_id),
        )
    ]
    desired = [b.to_dict() for b in boundaries]

    if dry_run:
        plan = plan_boundary_reconciliation(existing, desired)
        log.info("Section %s (dry run): %s", section_id, plan)
        return plan

    plan, _ = reconcile(
        db,
        get_macrostrat_table(db, "unit_boundaries"),
        existing=existing,
        desired=desired,
        key=_identity,
        owned_columns=AGE_MODEL_COLUMNS,
        scales=_COLUMN_SCALE,
    )
    log.info("Section %s: %s", section_id, plan)
    return plan
