"""Request and response models for boundary operations.

An operation's parameters are not modelled here: each operation's Pydantic model
in `macrostrat.map_topology.bounds.operations` is its schema, and
`/bounds/operations` publishes it so a client can build its form from the same
definition the CLI uses.
"""

from typing import Any, Optional

from pydantic import BaseModel


class OperationType(BaseModel):
    op_id: str
    description: str
    #: Drawn: carries a polygon (`add`, `subtract`).
    geometry: bool
    #: JSON Schema of the parameters.
    parameters: dict[str, Any]


class BoundaryOperation(BaseModel):
    id: int
    position: int
    operation: str
    parameters: dict[str, Any]
    note: Optional[str] = None
    error: Optional[str] = None
    #: GeoJSON, for drawn operations only; an opening's cached boundary is not sent.
    geometry: Optional[dict[str, Any]] = None


class MapBoundary(BaseModel):
    source_id: int
    slug: str
    name: Optional[str] = None
    area_km: Optional[float] = None
    boundary_error: Optional[str] = None
    #: `[minx, miny, maxx, maxy]` of the current boundary.
    bbox: Optional[list[float]] = None
    #: The operations have changed since the boundary was last built.
    needs_build: bool = False
    operations: list[BoundaryOperation] = []


class NewOperation(BaseModel):
    operation: str
    parameters: dict[str, Any] = {}
    #: GeoJSON Polygon or MultiPolygon, required by `add` and `subtract`.
    geometry: Optional[dict[str, Any]] = None
    note: Optional[str] = None


class OperationEdit(BaseModel):
    #: New position, 1 or greater.
    position: Optional[int] = None
    #: Replaces the note; an empty string clears it.
    note: Optional[str] = None


class BuildReport(BaseModel):
    dry_run: bool
    written: bool
    #: Rebuilt, but within tolerance of the stored boundary, so not written.
    unchanged: bool
    area_km: Optional[float] = None
    #: Area between the rebuilt and stored boundaries, km².
    diff_km: Optional[float] = None
    error: Optional[str] = None
    failed_operation_id: Optional[int] = None
    skipped: Optional[str] = None
