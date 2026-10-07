"""A map's boundary as an ordered list of operations, editable by admins.

The same edits as `macrostrat bounds add|rm|move|build`, through the same
library (`macrostrat.map_topology.bounds`), for the web boundary editor. Drawn
operations (`add`, `subtract`) are only possible here or in QGIS.

The routes are synchronous: the bounds library runs on the sync `Database`.
Building replays every operation in the database and can take minutes on a
continental map, so it is an explicit request, never a side effect of an edit.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import DatabaseDep
from api.routes.security import TokenData, require_admin
from macrostrat.map_topology.bounds import build as build_mod
from macrostrat.map_topology.bounds import edit
from macrostrat.map_topology.bounds.operations import (
    OPENING_OPERATIONS,
    OPERATIONS,
)

from .models import (
    BoundaryOperation,
    BuildReport,
    MapBoundary,
    NewOperation,
    OperationEdit,
    OperationType,
)

router = APIRouter(prefix="/bounds", tags=["bounds"])

AdminDep = Annotated[TokenData, Depends(require_admin)]


@router.get("/operations", summary="Boundary operations that can be appended")
def list_operations() -> list[OperationType]:
    """Each appendable operation with the JSON Schema of its parameters.

    Openings are left out: they are set from the CLI (`bounds open`).
    """
    return [
        OperationType(
            op_id=op_id,
            description=(cls.__doc__ or "").strip().split("\n")[0],
            geometry=cls.geometry_authored,
            parameters=cls.model_json_schema(),
        )
        for op_id, cls in OPERATIONS.items()
        if op_id not in OPENING_OPERATIONS
    ]


@router.get("/{ident}", summary="A map's boundary and its operations")
def get_boundary(ident: str, database: DatabaseDep) -> MapBoundary:
    """The boundary's summary and its ordered operations.

    The boundary geometry itself is not returned -- a continental one runs to
    tens of megabytes -- but is drawn from the tileserver's
    `/dev/topology/maps/{slug}` tiles.
    """
    return _boundary(database.sync, _source(database.sync, ident))


@router.post("/{ident}/operations", summary="Append an operation")
def append_operation(
    ident: str, body: NewOperation, database: DatabaseDep, user: AdminDep
) -> MapBoundary:
    """Append an operation at the end of the list. Admin only.

    The first edit pins the current boundary as the opening. Nothing is rebuilt.
    """
    db = database.sync
    source = _source(db, ident)
    with _edit(db):
        model = edit.validate(body.operation, body.parameters)
        edit.append(db, source.source_id, model, geometry=body.geometry, note=body.note)
    return _boundary(db, source)


@router.patch("/{ident}/operations/{op_id}", summary="Move or annotate an operation")
def edit_operation(
    ident: str,
    op_id: int,
    body: OperationEdit,
    database: DatabaseDep,
    user: AdminDep,
) -> MapBoundary:
    """Move an operation and/or replace its note. Admin only."""
    db = database.sync
    source = _source(db, ident)
    with _edit(db):
        if body.note is not None:
            edit.annotate(db, source.source_id, op_id, body.note or None)
        if body.position is not None:
            edit.move(db, source.source_id, op_id, body.position)
    return _boundary(db, source)


@router.delete("/{ident}/operations/{op_id}", summary="Remove an operation")
def remove_operation(
    ident: str, op_id: int, database: DatabaseDep, user: AdminDep
) -> MapBoundary:
    """Remove an operation; the ones after it move up. Admin only."""
    db = database.sync
    source = _source(db, ident)
    with _edit(db):
        edit.remove(db, source.source_id, op_id)
    return _boundary(db, source)


@router.post("/{ident}/build", summary="Rebuild the boundary from its operations")
def build_boundary(
    ident: str,
    database: DatabaseDep,
    user: AdminDep,
    dry_run: Annotated[
        bool, Query(description="Report the result without writing it")
    ] = True,
) -> BuildReport:
    """Replay the operations onto the boundary. Admin only; a dry run by default.

    A written boundary is re-noded by the next `macrostrat topo update`.
    """
    db = database.sync
    source = _source(db, ident)
    result = build_mod.build(db, source.source_id, dry_run=dry_run)
    return BuildReport(
        dry_run=dry_run,
        written=result.written,
        unchanged=result.unchanged,
        area_km=result.area_km,
        diff_km=result.diff_km,
        error=result.error,
        failed_operation_id=result.failed_op.id if result.failed_op else None,
        skipped=result.skipped,
    )


def _source(db, ident: str):
    source = db.run_query(
        "SELECT source_id, slug, name FROM maps.sources"
        " WHERE slug = :ident OR source_id::text = :ident",
        dict(ident=ident),
    ).first()
    if source is None:
        raise HTTPException(404, f"No map {ident!r}")
    return source


class _edit:
    """One edit, committed whole or not at all; a refused edit is a 400."""

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.db.session.commit()
            return False
        self.db.session.rollback()
        if isinstance(exc, edit.EditError):
            raise HTTPException(400, str(exc)) from exc
        return False


def _boundary(db, source) -> MapBoundary:
    area = db.run_query(
        f"""
        SELECT a.area_km, a.boundary_error,
          ARRAY[ST_XMin(b), ST_YMin(b), ST_XMax(b), ST_YMax(b)] AS bbox,
          EXISTS (SELECT 1 FROM map_bounds.boundary_op o WHERE o.source_id = a.source_id)
            AND a.ops_hash IS DISTINCT FROM (
              SELECT {build_mod.OPS_HASH} FROM map_bounds.boundary_op o
              WHERE o.source_id = a.source_id
            ) AS needs_build
        FROM map_bounds.map_area a, Box2D(a.geometry) b
        WHERE a.source_id = :source_id
        """,
        dict(source_id=source.source_id),
    ).first()
    ops = db.run_query(
        """
        SELECT id, position, operation, parameters, note, error,
          CASE WHEN operation IN ('add', 'subtract')
            THEN ST_AsGeoJSON(geometry, 6)::json END AS geometry
        FROM map_bounds.boundary_op
        WHERE source_id = :source_id
        ORDER BY position
        """,
        dict(source_id=source.source_id),
    ).all()
    return MapBoundary(
        source_id=source.source_id,
        slug=source.slug,
        name=source.name,
        area_km=area.area_km if area else None,
        boundary_error=area.boundary_error if area else None,
        bbox=list(area.bbox) if area else None,
        needs_build=bool(area and area.needs_build),
        operations=[
            BoundaryOperation(
                id=o.id,
                position=o.position,
                operation=o.operation,
                parameters=o.parameters if isinstance(o.parameters, dict) else {},
                note=o.note,
                error=o.error,
                geometry=o.geometry,
            )
            for o in ops
        ],
    )
