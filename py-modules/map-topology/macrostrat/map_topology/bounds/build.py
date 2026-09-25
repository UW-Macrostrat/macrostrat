"""Composing a map's boundary from its ordered operation list."""

from dataclasses import dataclass, field
from typing import Any

from macrostrat.database import Database

from .operations import COMPUTED_OPENINGS, OPENING_OPERATIONS, BoundaryOp, load

#: SQL yielding the running geometry inside the fold.
_SEED = "SELECT geometry FROM map_bounds.boundary_op WHERE id = :opening_id"

#: Geodesic area. A ring that wraps the globe is ambiguous on the sphere and the
#: geography type takes the smaller side, so bounds that cover the world -- the
#: `world` opening -- would come out as nothing. That case is the surface of the
#: WGS84 spheroid, stated.
_AREA_KM = """CASE
  WHEN ST_Covers({geom}, ST_MakeEnvelope(-180, -90, 180, 90, 4326)) THEN 510065621.7
  ELSE ST_Area(ST_Segmentize({geom}, 90)::geography) / 1e6
END"""


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
    opened: bool = False
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


#: SQL for each computed opening's geometry, given `:source_id`.
_OPENING_GEOMETRY = {
    # The map's own features.
    "union": """
        SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(geom)), 3))
        FROM maps.polygons
        WHERE source_id = :source_id
    """,
    # The bounds of every noded source below the compilation, read from the
    # topology: the faces their topogeometries hold form a coverage (the noding
    # already resolved every overlap), so they merge with `ST_CoverageUnion`
    # rather than an overlay. Half the time of `ST_Union` over the sources'
    # geometries for `medium` (20 s against 44 s), and exact: the bounds are the
    # region the compilation's faces will tile. Taking the noded sources rather
    # than the direct members makes the result independent of the order nested
    # compilations are built in; a mosaic is noded whole, so it counts and its
    # members do not. Nothing noded yet gives empty bounds, rebuilt when the
    # members' stamp changes.
    "compile": """
        SELECT coalesce(
          ST_Multi(ST_SetSRID(ST_CoverageUnion(
            topology.ST_GetFaceGeometry('map_bounds_topology', f.face_id)
          ), 4326)),
          ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)
        )
        FROM (
          SELECT DISTINCT r.element_id AS face_id
          FROM map_bounds.members_of(:source_id, true) m
          JOIN map_bounds.map_area a ON a.source_id = m.source_id
          JOIN map_bounds_topology.relation r
            ON r.layer_id = (a.topo).layer_id
           AND r.topogeo_id = (a.topo).id
           AND r.element_type = 3
          WHERE a.topo IS NOT NULL
        ) f
    """,
    # The whole world, by assertion.
    "world": "SELECT ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))",
}


def opening_operation(db: Database, source_id: int) -> tuple[int, str] | None:
    row = db.run_query(
        "SELECT id, operation FROM map_bounds.boundary_op"
        " WHERE source_id = :source_id AND position = 0",
        dict(source_id=source_id),
    ).first()
    if row is None:
        return None
    return row.id, row.operation


def set_opening(db: Database, source_id: int, operation: str) -> int:
    """Make `operation` the map's opening operation, replacing any existing one.

    The row's cached geometry is cleared; `build --init` (or `topo update`, for
    `compile`) recomputes it.
    """
    if operation not in OPENING_OPERATIONS:
        raise ValueError(f"{operation!r} cannot open a boundary")
    existing = opening_operation(db, source_id)
    if existing is None:
        return db.run_query(
            """
            INSERT INTO map_bounds.boundary_op (source_id, position, operation)
            VALUES (:source_id, 0, :operation)
            RETURNING id
            """,
            dict(source_id=source_id, operation=operation),
        ).scalar()
    db.run_query(
        "UPDATE map_bounds.boundary_op"
        " SET operation = :operation, geometry = NULL, parameters = jsonb_build_object()"
        " WHERE id = :id",
        dict(id=existing[0], operation=operation),
    )
    return existing[0]


def recompute_opening(db: Database, source_id: int) -> None:
    """Rebuild the cached geometry of a computed opening (`union`, `compile`, `world`).

    A map with no opening row is opened with `union`, as it always was.
    """
    opening = opening_operation(db, source_id)
    if opening is None:
        ensure_opening(db, source_id)
        opening = opening_operation(db, source_id)
        if opening is None:
            # No boundary to snapshot: open from the features directly.
            opening_id = db.run_query(
                """
                INSERT INTO map_bounds.boundary_op (source_id, position, operation)
                VALUES (:source_id, 0, 'union')
                RETURNING id
                """,
                dict(source_id=source_id),
            ).scalar()
            opening = (opening_id, "union")
    opening_id, operation = opening
    if operation not in COMPUTED_OPENINGS:
        return
    db.run_query(
        f"""
        UPDATE map_bounds.boundary_op
        SET geometry = ({_OPENING_GEOMETRY[operation]})
        WHERE id = :opening_id
        """,
        dict(source_id=source_id, opening_id=opening_id),
    )


# Kept under its old name for callers that only ever meant `union`.
recompute_union = recompute_opening


def _fold(
    ops: list[OpRow], upto: int | None = None, *, seed: str | None = None
) -> tuple[str, dict[str, Any]]:
    """Build one SQL expression applying `ops` in order.

    Geometry never leaves the database: the operations nest into a single
    expression rather than round-tripping through Python.
    """
    params: dict[str, Any] = {}
    start = 0
    if seed is None:
        seed = _SEED
        params["opening_id"] = ops[0].id
        start = 1
    elif ops and ops[0].position == 0 and ops[0].operation in OPENING_OPERATIONS:
        # The seed stands in for the opening row.
        start = 1
    expr = f"({seed})"
    for i, row in enumerate(ops[start : upto if upto is None else upto], start=1):
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

    if init and not dry_run:
        recompute_opening(db, source_id)

    ops = load_ops(db, source_id)

    if not ops:
        # Nothing to replay. The boundary is whatever the union pipeline last
        # produced, which is already in map_area.geometry.
        result.ops = ops
        result.skipped = "no operations"
        return result

    seed = None
    if (
        ops[0].position == 0
        and ops[0].operation in COMPUTED_OPENINGS
        and not ops[0].has_geometry
    ):
        # A computed opening whose cache was never filled (`bounds open`, or a
        # compilation seeded with `compile` or `world`): compute it now. A dry
        # run must not write, so it folds over the opening's SQL instead.
        if dry_run:
            seed = _OPENING_GEOMETRY[ops[0].operation]
        else:
            recompute_opening(db, source_id)
            ops = load_ops(db, source_id)
    if ops[0].position != 0:
        # Operations authored outside the CLI -- QGIS edits `boundary_op`
        # directly -- have no opening row. Fill it from the current boundary
        # rather than refusing: the geometry is taken as read, but it has to be
        # *pinned* into position 0, because the fold otherwise reads its base
        # from the same column it writes and would re-apply it on every run.
        #
        # A dry run must not write, so it folds over `map_area.geometry`
        # directly instead -- the same geometry the opening row would capture.
        if dry_run:
            seed = (
                "SELECT geometry FROM map_bounds.map_area WHERE source_id = :source_id"
            )
        elif ensure_opening(db, source_id) is None:
            result.error = (
                "no boundary geometry to open from; "
                "run with --init to compute one from the map's features"
            )
            return result
        else:
            db.session.commit()
            result.opened = True
            ops = load_ops(db, source_id)

    result.ops = ops

    # With an explicit seed there is deliberately no opening row to check.
    if seed is None and ops[0].operation not in OPENING_OPERATIONS:
        result.error = (
            f"position 0 holds {ops[0].operation!r}, which cannot open a boundary"
        )
        return result

    expr, params = _fold(ops, seed=seed)
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
                boundary_error = NULL,
                geometry_hash = NULL
            WHERE source_id = :source_id
            RETURNING {_AREA_KM.format(geom="geometry")} AS area_km
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
