"""Write columns and column groups, reconciling against what is already there.

Replaces the previous `get_or_create_column`, which matched on `(col_name, project_id)`
and filled the NOT NULL columns it did not understand with placeholder zeros —
`col_position=""`, `col_area=0`, `col=0`, `lat=0`, `lng=0`. Geometry now comes from
`geometry.resolve_geometry` (PostGIS via `geoalchemy2`), and the rest goes through the
shared reconciler.

Natural keys
------------

| table | key |
| --- | --- |
| `col_groups` | `(project_id, col_group)` |
| `cols` | `(project_id, col_group_id, col_name)` |

Measured across the corpus, `(project_id, col_group_id, col_name)` leaves 39 rows in
colliding groups, against 146 for `(project_id, col_name)`; adding `col_type` gains
nothing further.
"""

from datetime import datetime, timezone

from macrostrat.utils import get_logger

from ..database import get_macrostrat_table
from ..reconciliation import ReconciliationPlan, reconcile
from .geometry import resolve_geometry
from .parse import Column

log = get_logger(__name__)

COL_GROUP_KEY = ("project_id", "col_group")
COL_GROUP_COLUMNS = ("col_group_long",)

COL_KEY = ("project_id", "col_group_id", "col_name")
#: `created` is deliberately absent: it records when the row was first written and is set
#: on INSERT only.
COL_COLUMNS = (
    "status_code",
    "col_type",
    "col_position",
    "col",
    "lat",
    "lng",
    "col_area",
    "coordinate",
    "poly_geom",
    "wkt",
)
COL_SCALES = {"lat": 5, "lng": 5}  # numeric(8,5)


def reconcile_column_group(
    db, project_id: int, name: str = "Default", long_name: str | None = None
) -> int:
    """Get or create a column group, returning its id."""
    desired = [
        {
            "project_id": project_id,
            "col_group": name,
            "col_group_long": long_name or f"{name} column group",
        }
    ]
    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, project_id, col_group, col_group_long
            FROM macrostrat.col_groups
            WHERE project_id = :project_id AND col_group = :col_group
            ORDER BY id
            """,
            dict(project_id=project_id, col_group=name),
        )
    ]
    _, ids = reconcile(
        db,
        get_macrostrat_table(db, "col_groups"),
        existing=existing,
        desired=desired,
        key=COL_GROUP_KEY,
        owned_columns=COL_GROUP_COLUMNS,
    )
    return ids[0]


def _column_number(col: Column, fallback: int) -> float:
    """`cols.col` is a NOT NULL numeric column number.

    Use the workbook's own identifier when it is numeric — that is what an operator means
    by a column number — and otherwise fall back to an ordinal so the value is at least
    stable within a run.
    """
    try:
        return float(col.local_id)
    except (TypeError, ValueError):
        return float(fallback)


def _desired_column_row(db, col: Column, ordinal: int) -> dict:
    geometry = resolve_geometry(
        db,
        lat=col.lat,
        lng=col.lng,
        geom=col.geom or col.rgeom,
        label=f"column {col.local_id or col.name!r}",
    )
    return {
        "project_id": col.project_id,
        "col_group_id": col.group_id,
        "col_name": col.name,
        "status_code": col.status_code,
        "col_type": col.col_type,
        "col_position": "",
        "col": _column_number(col, ordinal),
        **geometry.column_values(),
    }


def reconcile_columns(
    db, columns: list[Column], *, project_id: int, col_group_id: int
) -> ReconciliationPlan:
    """Reconcile a project's columns, setting `col.id` on each.

    Geometry failures are collected and raised together, so an operator sees every bad
    row in one pass rather than one per run.
    """
    if not columns:
        return ReconciliationPlan()

    desired, problems = [], []
    for ordinal, col in enumerate(columns, start=1):
        col.project_id = project_id
        col.group_id = col_group_id
        try:
            desired.append(_desired_column_row(db, col, ordinal))
        except ValueError as err:
            problems.append(str(err))
    if problems:
        raise ValueError(
            f"{len(problems)} column(s) have unusable geometry:\n  "
            + "\n  ".join(problems)
        )

    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, project_id, col_group_id, col_name, status_code, col_type,
                   col_position, col, lat, lng, col_area, wkt
            FROM macrostrat.cols
            WHERE project_id = :project_id AND col_group_id = :col_group_id
            ORDER BY id
            """,
            dict(project_id=project_id, col_group_id=col_group_id),
        )
    ]

    # `coordinate` and `poly_geom` are omitted from the comparison above: they are
    # derived from `wkt`, which is compared, so refetching the geometries to diff them
    # would cost a round trip and tell us nothing new.
    now = datetime.now(timezone.utc)
    for row in desired:
        row.setdefault("created", now)

    plan, ids = reconcile(
        db,
        get_macrostrat_table(db, "cols"),
        existing=existing,
        desired=desired,
        key=COL_KEY,
        owned_columns=COL_COLUMNS,
        scales=COL_SCALES,
    )
    for col, col_id in zip(columns, ids):
        col.id = col_id

    log.info("columns: %s", plan)
    return plan
