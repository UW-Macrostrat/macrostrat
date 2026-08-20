"""Age modeling: turning age constraints on stratigraphic surfaces into `unit_boundaries`.

- `model` — the general, principled machinery. `AgeModel` interpolates ages for
  surfaces that carry no constraint of their own, and `AgeModel.axis_position` is
  the seam subclasses use when a column's positions mean something other than
  metric distance.
- `reconciliation` — writing a rebuilt model back without churning row identity.
  Carries a standing TODO to replace most of itself with a unique constraint.
- `eodp` — recovering constraints from the legacy `fo`/`lo` fields on ocean-drilling
  columns, the one place eODP-specific assumptions are allowed to live.
- `approaches` — which of the above a given column needs, and the entry point the
  CLI calls.

The `units.fo` / `lo` / `fo_h` / `lo_h` policy
---------------------------------------------
`unit_boundaries` is the source of truth for age control. The four legacy columns on
`macrostrat.units` are handled as follows, and **nothing should deviate without
updating this note**:

- **`fo`, `lo` are computed outputs.** Derive them from the finished age model — the
  narrowest interval containing the unit's modelled bottom and top age respectively
  (`AgeModel._containing_interval` does that lookup). They are never read from a
  workbook and never hand-authored. They stay NOT NULL because there is no interval `0`
  to fall back on (the `DEFAULT 0` on those columns is a dead default), and because
  `lookup-unit-intervals-01.sql` reaches them through *inner* joins — a NULL `fo` would
  silently drop the unit from the lookup rebuild rather than fail.

- **`fo_h`, `lo_h` are ignored.** Not read, not written; existing values left alone.
  In particular do **not** adopt a `prop * 10000` encoding for them: the maximum `fo_h`
  in the table is 255, so that scale is a new invention rather than the legacy
  convention. It appeared only in the since-removed project-metadata importer's mapping
  file and never took root.

`eodp` is the deliberate exception: it *reads* `fo`/`lo` because that is where the
ocean-drilling columns' age control currently lives. It is a migration tool, not a
permanent fixture. The long-term target is that every column expresses its age control
as `unit_boundaries` rows, leaving `fo`/`lo` as purely derived shadows for the legacy
consumers, at which point the special-case approaches retire one dataset at a time.

See `Investigations/Column ingestion architecture.md` for the reasoning, and
`Investigations/Age model creation from legacy fields.md` for the eODP decoding.
"""

from .approaches import (
    AgeModelApproach,
    default_approach_for_column,
    recalculate_column_age_model,
)
from .model import (
    AgeModel,
    AgeModelSurface,
    BoundaryStatus,
    UnitBoundary,
    build_age_model,
    build_age_model_for_existing_column,
    build_section_age_model,
    create_unit_boundaries,
    remove_existing_age_model,
)
from .reconciliation import (
    AGE_MODEL_COLUMNS,
    BoundaryPlan,
    no_unit,
    plan_boundary_reconciliation,
    reconcile_unit_boundaries,
    write_unit_boundaries,
)

__all__ = [
    "AGE_MODEL_COLUMNS",
    "AgeModelApproach",
    "AgeModel",
    "AgeModelSurface",
    "BoundaryPlan",
    "BoundaryStatus",
    "UnitBoundary",
    "build_age_model",
    "build_age_model_for_existing_column",
    "build_section_age_model",
    "create_unit_boundaries",
    "default_approach_for_column",
    "no_unit",
    "plan_boundary_reconciliation",
    "recalculate_column_age_model",
    "reconcile_unit_boundaries",
    "remove_existing_age_model",
    "write_unit_boundaries",
]
