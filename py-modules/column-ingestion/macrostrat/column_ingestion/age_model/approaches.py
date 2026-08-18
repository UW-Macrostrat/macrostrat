"""Which age-modeling approach a column needs.

Most columns are handled by the general model in `model`. A few sets of columns
carry assumptions the general model cannot infer — currently just the
ocean-drilling columns, whose age control lives in the legacy `units.fo` / `lo`
fields rather than in `unit_boundaries`.

Rather than have callers know which is which, `default_approach_for_column` looks
it up. Add cases to `_APPROACH_BY_PROJECT` as they come up; keying on the project
*slug* rather than its id keeps the mapping readable and stable across databases.
"""

from enum import Enum

from macrostrat.utils import get_logger

from .reconciliation import BoundaryPlan

log = get_logger(__name__)


class AgeModelApproach(str, Enum):
    """How to derive the age constraints a model is built from."""

    #: The general, principled path: constraints come from `unit_boundaries`
    #: and per-unit relative ages, and time is spread along measured position.
    DEFAULT = "default"

    #: Recover constraints from the legacy `fo`/`lo` fields, and spread time along
    #: cumulative recovered thickness. See `eodp`.
    EODP = "eodp"


#: Projects whose columns need something other than the general approach.
_APPROACH_BY_PROJECT = {
    "eodp": AgeModelApproach.EODP,
}


def project_slug_for_column(db, col_id: int) -> str | None:
    return db.run_query(
        """
        SELECT p.slug
        FROM macrostrat.cols c
        LEFT JOIN macrostrat.projects p ON p.id = c.project_id
        WHERE c.id = :col_id
        """,
        dict(col_id=col_id),
    ).scalar()


def default_approach_for_column(db, col_id: int) -> AgeModelApproach:
    """The approach a column should use unless the caller overrides it."""
    slug = project_slug_for_column(db, col_id)
    approach = _APPROACH_BY_PROJECT.get(slug, AgeModelApproach.DEFAULT)
    log.debug("Column %s (project %s) -> %s approach", col_id, slug, approach.value)
    return approach


def recalculate_column_age_model(
    db,
    col_id: int,
    *,
    approach: AgeModelApproach | None = None,
    dry_run: bool = False,
) -> tuple[AgeModelApproach, dict[int, BoundaryPlan]]:
    """Rebuild a column's age model, choosing the approach if not given.

    Returns the approach used and the reconciliation plan for each section, so a
    caller can report what actually changed.
    """
    if approach is None:
        approach = default_approach_for_column(db, col_id)

    if approach is AgeModelApproach.EODP:
        from .eodp import build_eodp_age_model_for_existing_column

        plans = build_eodp_age_model_for_existing_column(db, col_id, dry_run=dry_run)
    else:
        from .model import build_age_model_for_existing_column

        plans = build_age_model_for_existing_column(db, col_id, dry_run=dry_run)

    return approach, plans
