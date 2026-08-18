"""Match freshly-built rows onto rows already in the database, preserving identity.

Rebuilding derived data used to mean deleting a section's rows and inserting fresh
ones. That burns an id per row on every run, gives every row a new identity, and —
where other tables reference it with `ON DELETE CASCADE` — destroys work nobody asked
us to touch. Instead we match on a declared **natural key**, update in place what
moved, insert what is new, and delete only what is genuinely dereferenced.

`plan_reconciliation` is pure — plain dicts in, a `ReconciliationPlan` out — so the
matching rules are testable without a database. `apply_reconciliation` executes a plan,
and `reconcile` does both in one step; the four statements involved are identical for
every entity once the table and columns are known, so they are generated rather than
written out per entity. Both return an id for **every** desired row, matched or inserted,
which is what callers need to attach ids to objects or write dependent rows — and means
nobody re-derives the pairing and risks disagreeing with the plan.

Callers supply three things:

- **`key`** — the natural key. A sequence of column names, or a callable for keys that
  need normalising (e.g. `unit_boundaries`, where a legacy `0` and a modern `NULL` mean
  the same "no unit on this side").
- **`owned_columns`** — the only columns an update is allowed to write. Everything else
  on a matched row is somebody else's: curated fields, or key components that must not
  drift.
- **`scales`** — decimal places per column, so a rebuilt value is compared against the
  database at the precision the database actually stores. Without this, float noise in
  the ninth decimal marks every row changed and identity is preserved in name only.

None of the natural keys in play are unique in the database yet. Duplicates within a
key group are matched positionally and any surplus lands in `deletes`, which
incidentally cleans them up. See `age_model.reconciliation` for the standing TODO on
replacing this with real unique constraints and an upsert.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from sqlalchemy import Table

KeySpec = Sequence[str] | Callable[[dict], tuple]


@dataclass
class ReconciliationPlan:
    """What reconciling a set of rows would do. Ids refer to existing rows."""

    updates: list[tuple[int, dict]] = field(default_factory=list)
    inserts: list[dict] = field(default_factory=list)
    deletes: list[int] = field(default_factory=list)
    unchanged: list[int] = field(default_factory=list)
    #: For each `desired` row, in input order: the id of the existing row it matched, or
    #: `None` if it needs inserting. Recording the pairing here means callers that need
    #: the resulting ids — to attach them to objects, or to write child rows — never
    #: have to re-derive the matching and risk disagreeing with the plan.
    matched: list[int | None] = field(default_factory=list)

    @property
    def is_noop(self) -> bool:
        return not (self.updates or self.inserts or self.deletes)

    def __str__(self):
        return (
            f"{len(self.unchanged)} unchanged, {len(self.updates)} updated, "
            f"{len(self.inserts)} inserted, {len(self.deletes)} deleted"
        )


def _key_function(key: KeySpec) -> Callable[[dict], tuple]:
    if callable(key):
        return key
    columns = tuple(key)
    return lambda row: tuple(row.get(c) for c in columns)


def _quantizer(scales: Mapping[str, int] | None) -> Callable[[str, object], object]:
    scales = scales or {}

    def quantize(column: str, value):
        scale = scales.get(column)
        if value is None or scale is None:
            return value
        return round(float(value), scale)

    return quantize


def plan_reconciliation(
    existing: list[dict],
    desired: list[dict],
    *,
    key: KeySpec,
    owned_columns: Sequence[str],
    scales: Mapping[str, int] | None = None,
) -> ReconciliationPlan:
    """Plan the updates, inserts and deletes that reconcile `desired` onto `existing`.

    `existing` rows must carry `id` alongside the key and owned columns. A row whose
    key still matches keeps its `id`, and is only updated if one of `owned_columns`
    actually moved at stored precision.
    """
    identity = _key_function(key)
    quantize = _quantizer(scales)
    owned = tuple(owned_columns)

    by_key: dict[tuple, deque] = defaultdict(deque)
    for row in existing:
        by_key[identity(row)].append(row)

    plan = ReconciliationPlan()

    # Pair each desired row with an existing row of the same key, if one is left.
    paired: list[tuple[dict | None, dict]] = []
    for row in desired:
        queue = by_key.get(identity(row))
        paired.append((queue.popleft() if queue else None, row))

    for current, row in paired:
        plan.matched.append(None if current is None else current["id"])
        if current is None:
            plan.inserts.append(dict(row))
            continue
        values = {c: quantize(c, row.get(c)) for c in owned}
        changed = any(v != quantize(c, current.get(c)) for c, v in values.items())
        if changed:
            plan.updates.append((current["id"], values))
        else:
            plan.unchanged.append(current["id"])

    # Whatever is left over no longer corresponds to anything we would build.
    for queue in by_key.values():
        plan.deletes.extend(row["id"] for row in queue)

    return plan


def apply_reconciliation(
    db,
    table: Table,
    plan: ReconciliationPlan,
    desired: list[dict],
    *,
    owned_columns: Sequence[str],
) -> list[int]:
    """Execute a plan against `table` and return an id for every `desired` row.

    Takes a SQLAlchemy `Table` rather than a name so statements are built through Core.
    That keeps the four statements generated rather than written out per entity, and it
    means typed values bind correctly — notably `geoalchemy2` geometries, which need the
    column's type to render as `ST_GeomFromEWKT(...)` and would be inserted as raw text
    through a plain string query.

    Returns ids aligned with `desired`, which is what callers need in order to attach them
    to objects or to write dependent rows.
    """
    if owned_columns:
        for row_id, values in plan.updates:
            db.session.execute(
                table.update().where(table.c.id == row_id).values(**values)
            )

    ids: list[int] = list(plan.matched)
    for position, row_id in enumerate(ids):
        if row_id is not None:
            continue
        ids[position] = db.session.execute(
            table.insert().values(**desired[position]).returning(table.c.id)
        ).scalar()

    if plan.deletes:
        db.session.execute(table.delete().where(table.c.id.in_(plan.deletes)))

    return ids


def reconcile(
    db,
    table: Table,
    *,
    existing: list[dict],
    desired: list[dict],
    key: KeySpec,
    owned_columns: Sequence[str],
    scales: Mapping[str, int] | None = None,
) -> tuple[ReconciliationPlan, list[int]]:
    """Plan and apply in one step. Returns the plan and an id per `desired` row."""
    plan = plan_reconciliation(
        existing, desired, key=key, owned_columns=owned_columns, scales=scales
    )
    ids = apply_reconciliation(db, table, plan, desired, owned_columns=owned_columns)
    return plan, ids
