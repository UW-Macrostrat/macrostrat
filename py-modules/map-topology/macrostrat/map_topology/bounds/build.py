"""Composing a map's boundary from its ordered operation list."""

from dataclasses import dataclass, field
from typing import Any

from macrostrat.database import Database

from .operations import OPENING_OPERATIONS, BoundaryOp, load

#: SQL yielding the running geometry inside the fold.
_SEED = "SELECT geometry FROM map_bounds.boundary_op WHERE id = :opening_id"

_AREA_KM = "ST_Area(ST_Segmentize({geom}, 90)::geography) / 1e6"


@dataclass
class OpRow:
    id: int
    position: int
    operation: str
    has_geometry: bool
    note: str | None
    op: BoundaryOp


@dataclass
class BuildResult:
    source_id: int
    slug: str | None = None
    ops: list[OpRow] = field(default_factory=list)
    area_km: float | None = None
    written: bool = False
    error: str | None = None
    failed_op: OpRow | None = None
    skipped: str | None = None


def load_ops(db: Database, source_id: int) -> list[OpRow]:
    rows = db.run_query(
        """
        SELECT id, position, operation, geometry IS NOT NULL AS has_geometry,
               note, parameters
        FROM map_bounds.boundary_op
        WHERE source_id = :source_id
        ORDER BY position
        """,
        dict(source_id=source_id),
    ).all()
    return [
        OpRow(
            id=r.id,
            position=r.position,
            operation=r.operation,
            has_geometry=r.has_geometry,
            note=r.note,
            op=load(r.operation, r.parameters),
        )
        for r in rows
    ]


def ensure_opening(db: Database, source_id: int) -> int | None:
    """Pin the map's current boundary as a position-0 operation.

    Called before the first operation is added. The existing `map_area.geometry`
    is taken as read -- no union is recomputed -- but it must be *captured*,
    because `build` would otherwise read its base from the same column it
    writes, re-applying every operation on each run.

    Labelled `union` because that is what it is: every existing boundary was
    produced by the union pipeline.
    """
    existing = db.run_query(
        "SELECT id FROM map_bounds.boundary_op"
        " WHERE source_id = :source_id AND position = 0",
        dict(source_id=source_id),
    ).scalar()
    if existing is not None:
        return existing
    return db.run_query(
        """
        INSERT INTO map_bounds.boundary_op
          (source_id, position, operation, geometry, note)
        SELECT source_id, 0, 'union', geometry,
               'Snapshot of the boundary as it stood when editing began'
        FROM map_bounds.map_area
        WHERE source_id = :source_id AND geometry IS NOT NULL
        RETURNING id
        """,
        dict(source_id=source_id),
    ).scalar()


def recompute_union(db: Database, source_id: int) -> None:
    """Rebuild the cached opening union from the map's own features."""
    opening = db.run_query(
        "SELECT id FROM map_bounds.boundary_op"
        " WHERE source_id = :source_id AND position = 0 AND operation = 'union'",
        dict(source_id=source_id),
    ).scalar()
    if opening is None:
        ensure_opening(db, source_id)
        opening = db.run_query(
            "SELECT id FROM map_bounds.boundary_op"
            " WHERE source_id = :source_id AND position = 0",
            dict(source_id=source_id),
        ).scalar()
    db.run_query(
        """
        UPDATE map_bounds.boundary_op
        SET geometry = (
            SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(geom)), 3))
            FROM maps.polygons
            WHERE source_id = :source_id
        )
        WHERE id = :opening_id
        """,
        dict(source_id=source_id, opening_id=opening),
    )


def _fold(ops: list[OpRow], upto: int | None = None) -> tuple[str, dict[str, Any]]:
    """Build one SQL expression applying `ops` in order.

    Geometry never leaves the database: the operations nest into a single
    expression rather than round-tripping through Python.
    """
    params: dict[str, Any] = {}
    opening = ops[0]
    params["opening_id"] = opening.id
    expr = f"({_SEED})"
    for i, row in enumerate(ops[1 : upto if upto is None else upto], start=1):
        key = f"operand_{i}"
        params[key] = row.id
        operand = (
            f"(SELECT geometry FROM map_bounds.boundary_op WHERE id = :{key})"
            if row.has_geometry
            else "NULL::geometry"
        )
        sub: dict[str, Any] = {}
        expr = row.op.sql(expr, sub, operand)
        # Keep per-operation parameter names distinct across the fold.
        for k, v in sub.items():
            params[f"{k}_{i}"] = v
            expr = expr.replace(f":{k}", f":{k}_{i}")
    return expr, params


def build(db: Database, source_id: int, *, init: bool = False, dry_run: bool = False):
    """Replay a map's operations onto `map_area.geometry`."""
    result = BuildResult(source_id=source_id)
    result.slug = db.run_query(
        "SELECT slug FROM maps.sources WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).scalar()

    if init:
        recompute_union(db, source_id)

    ops = load_ops(db, source_id)
    result.ops = ops

    if not ops:
        # Nothing to replay. The boundary is whatever the union pipeline last
        # produced, which is already in map_area.geometry.
        result.skipped = "no operations"
        return result
    if ops[0].operation not in OPENING_OPERATIONS:
        result.error = (
            f"first operation is {ops[0].operation!r} at position "
            f"{ops[0].position}; no opening operation at position 0"
        )
        return result

    expr, params = _fold(ops)
    params["source_id"] = source_id

    if dry_run:
        row = db.run_query(
            f"SELECT ST_GeometryType(g) AS gtype, {_AREA_KM.format(geom='g')}"
            f" AS area_km FROM (SELECT {expr} AS g) s",
            params,
        ).first()
        result.area_km = row.area_km
        return result

    try:
        row = db.run_query(
            f"""
            UPDATE map_bounds.map_area
            SET geometry = ({expr}),
                boundary_error = NULL
            WHERE source_id = :source_id
            RETURNING {_AREA_KM.format(geom='geometry')} AS area_km
            """,
            params,
        ).first()
    except Exception as err:  # noqa: BLE001 -- recorded as data, see below
        db.session.rollback()
        result.error = str(err).strip().splitlines()[0]
        result.failed_op = _locate_failure(db, ops, params)
        _record_error(db, source_id, result)
        return result

    # area_km is derived, so set it in the same pass rather than leaving it stale.
    db.run_query(
        f"UPDATE map_bounds.map_area"
        f" SET area_km = {_AREA_KM.format(geom='geometry')}"
        f" WHERE source_id = :source_id",
        dict(source_id=source_id),
    )
    db.run_query(
        "UPDATE map_bounds.boundary_op SET error = NULL"
        " WHERE source_id = :source_id AND error IS NOT NULL",
        dict(source_id=source_id),
    )
    db.session.commit()
    result.area_km = row.area_km
    result.written = True
    return result


def _locate_failure(db: Database, ops: list[OpRow], _params) -> OpRow | None:
    """Find the first operation that fails, by replaying prefixes.

    Only runs on the error path, so the repeated work is acceptable in exchange
    for pointing at a specific operation rather than the whole list.
    """
    for upto in range(2, len(ops) + 1):
        expr, params = _fold(ops, upto=upto)
        try:
            db.run_query(f"SELECT ST_IsValid({expr})", params).scalar()
        except Exception:  # noqa: BLE001
            db.session.rollback()
            return ops[upto - 1]
    return None


def _record_error(db: Database, source_id: int, result: BuildResult) -> None:
    db.run_query(
        "UPDATE map_bounds.map_area SET boundary_error = :err"
        " WHERE source_id = :source_id",
        dict(source_id=source_id, err=result.error),
    )
    if result.failed_op is not None:
        db.run_query(
            "UPDATE map_bounds.boundary_op SET error = :err WHERE id = :id",
            dict(id=result.failed_op.id, err=result.error),
        )
    db.session.commit()
