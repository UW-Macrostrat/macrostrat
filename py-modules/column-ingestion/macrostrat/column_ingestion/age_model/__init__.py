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
