"""Editing a map's operation list: append, remove, move, annotate.

Shared by the CLI and the API. Nothing here commits: the caller decides what one
edit is, so a batch is never left half-applied.
"""

import json
from typing import Any

from macrostrat.database import Database

from .build import OpRow, ensure_opening, load_ops
from .operations import OPENING_OPERATIONS, BoundaryOp, load


class EditError(ValueError):
    """An edit the operation list cannot take."""


#: A drawn GeoJSON polygon, made valid and multi to fit `boundary_op.geometry`.
_GEOMETRY = (
    "ST_Multi(ST_CollectionExtract(ST_MakeValid("
    "ST_SetSRID(ST_GeomFromGeoJSON(CAST(:geometry AS text)), 4326)), 3))"
)


def validate(operation: str, parameters: Any) -> BoundaryOp:
    """The operation's model, or an `EditError` naming what is wrong."""
    if operation in OPENING_OPERATIONS:
        raise EditError(f"{operation} is an opening; it cannot be appended")
    try:
        return load(operation, parameters)
    except Exception as err:  # noqa: BLE001 -- pydantic or unknown operation
        raise EditError(str(err)) from err


def append(
    db: Database,
    source_id: int,
    model: BoundaryOp,
    *,
    geometry: dict | str | None = None,
    note: str | None = None,
) -> int:
    """Append an operation at the end of the list; returns its id.

    Pins the current boundary as the opening first, if the list has none.
    `geometry` is GeoJSON, required by `add` and `subtract` and refused by the
    rest.
    """
    if model.geometry_authored and geometry is None:
        raise EditError(f"{model.op_id} needs a geometry")
    if not model.geometry_authored and geometry is not None:
        raise EditError(f"{model.op_id} takes no geometry")
    if ensure_opening(db, source_id) is None:
        raise EditError(
            f"Source {source_id} has no boundary to build on;"
            " run `macrostrat bounds build --init` first"
        )
    if isinstance(geometry, dict):
        geometry = json.dumps(geometry)

    geometry_sql = _GEOMETRY if geometry is not None else "NULL"
    return db.run_query(
        f"""
        INSERT INTO map_bounds.boundary_op
          (source_id, position, operation, parameters, geometry, note)
        SELECT :source_id, coalesce(max(position), 0) + 1, :operation,
               CAST(:parameters AS jsonb), {geometry_sql}, :note
        FROM map_bounds.boundary_op WHERE source_id = :source_id
        RETURNING id
        """,
        dict(
            source_id=source_id,
            operation=model.op_id,
            parameters=model.model_dump_json(),
            geometry=geometry,
            note=note,
        ),
    ).scalar()


def remove(db: Database, source_id: int, op_id: int) -> OpRow:
    """Delete an operation and close the gap it leaves; returns what was removed."""
    ops = load_ops(db, source_id)
    target = _movable(ops, op_id, source_id)
    db.run_query("DELETE FROM map_bounds.boundary_op WHERE id = :id", dict(id=op_id))
    _renumber(db, [o for o in ops if o.position > 0 and o.id != op_id])
    return target


def move(db: Database, source_id: int, op_id: int, position: int) -> int:
    """Move an operation to `position` (1 or greater); returns where it landed."""
    if position < 1:
        raise EditError("Position 0 is reserved for the opening operation")
    ops = [o for o in load_ops(db, source_id) if o.position > 0]
    target = _movable(ops, op_id, source_id)
    ops.remove(target)
    ops.insert(min(position, len(ops) + 1) - 1, target)
    _renumber(db, ops)
    return ops.index(target) + 1


def annotate(db: Database, source_id: int, op_id: int, note: str | None) -> None:
    updated = db.run_query(
        "UPDATE map_bounds.boundary_op SET note = :note"
        " WHERE id = :id AND source_id = :source_id",
        dict(id=op_id, source_id=source_id, note=note),
    ).rowcount
    if not updated:
        raise EditError(f"No operation {op_id} on source {source_id}")


def set_geometry(
    db: Database, source_id: int, op_id: int, geometry: dict | str
) -> None:
    """Replace a drawn operation's polygon with GeoJSON."""
    target = next((o for o in load_ops(db, source_id) if o.id == op_id), None)
    if target is None:
        raise EditError(f"No operation {op_id} on source {source_id}")
    if not target.op.geometry_authored:
        raise EditError(f"{target.operation} has no drawn geometry to replace")
    if isinstance(geometry, dict):
        geometry = json.dumps(geometry)
    db.run_query(
        f"UPDATE map_bounds.boundary_op SET geometry = {_GEOMETRY} WHERE id = :id",
        dict(id=op_id, geometry=geometry),
    )


def _movable(ops: list[OpRow], op_id: int, source_id: int) -> OpRow:
    target = next((o for o in ops if o.id == op_id), None)
    if target is None:
        raise EditError(f"No operation {op_id} on source {source_id}")
    if target.position == 0:
        raise EditError("The opening operation cannot be moved or removed")
    return target


def _renumber(db: Database, ops: list[OpRow]) -> None:
    """Write a clean 1..N sequence.

    The unique position constraint only holds again once every row has moved,
    so it is deferred for the transaction.
    """
    db.run_query("SET CONSTRAINTS map_bounds.boundary_op_unique_position DEFERRED")
    for index, o in enumerate(ops, start=1):
        if o.position != index:
            db.run_query(
                "UPDATE map_bounds.boundary_op SET position = :position WHERE id = :id",
                dict(id=o.id, position=index),
            )
