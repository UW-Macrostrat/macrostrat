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
| `cols` | `(project_id, orig_id)` where present, else `(project_id, col_group_id, col_name)` |

Measured across the corpus, `(project_id, col_group_id, col_name)` leaves 39 rows in
colliding groups, against 146 for `(project_id, col_name)`; adding `col_type` gains
nothing further. It remains the fallback for workbook columns, which carry no source
identifier — see `column_identity` for why an ingested dataset cannot rely on it.
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


def column_identity(row: dict) -> tuple:
    """Natural key of a column, preferring `orig_id` over the name.

    `macrostrat.cols.orig_id` is the identifier the column carries in the dataset it came
    from, and it takes precedence because `col_name` is not dependable as identity for an
    ingested dataset: 11,548 of GBDB's 29,328 sections share a name with another section
    (`Guanyinqiao` names 53 of them). Duplicates within a key group are matched
    positionally, so without `orig_id` a column's identity is "the Nth Guanyinqiao by
    insertion order" — stable only while the desired set is byte-identical, and so broken
    by a new export or merely by a different `--limit`.

    The leading discriminant keeps the two keys in one namespace without colliding, so a
    project may hold both ingested and hand-authored columns.
    """
    orig_id = row.get("orig_id")
    if orig_id is not None and str(orig_id).strip() != "":
        return ("orig_id", row.get("project_id"), str(orig_id).strip())
    return ("name",) + tuple(row.get(c) for c in COL_KEY)


#: Columns on `cols` this writer owns and may overwrite on a matched row.
#:
#: `created` is deliberately absent: it records when the row was first written and is set
#: on INSERT only. `orig_id` is absent for the same reason — it is identity, so a matched
#: row keeps whatever it has rather than having it rewritten.
#:
#: `col_name` *is* here, so that a column matched by `orig_id` picks up an upstream
#: rename. For a name-matched row the update is a provable no-op, since the name is its
#: key.
COL_COLUMNS = (
    "col_name",
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
        "orig_id": col.orig_id,
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

    # Scoped to one column group, not to the project, because anything in `existing`
    # that no longer corresponds to a desired row is deleted — a project-wide fetch would
    # prune every other group. The consequence is that a column which changed group is not
    # found here and is inserted, which the `(project_id, orig_id)` unique index then
    # rejects. That is a loud failure rather than a silent duplicate, and this ingest path
    # gives a project a single "Default" group, so it is not reachable today.
    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, project_id, col_group_id, col_name, orig_id, status_code,
                   col_type, col_position, col, lat, lng, col_area, wkt
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
        key=column_identity,
        owned_columns=COL_COLUMNS,
        scales=COL_SCALES,
    )
    for col, col_id in zip(columns, ids):
        col.id = col_id

    log.info("columns: %s", plan)
    return plan
