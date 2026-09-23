"""Boundary operations: one Pydantic model per operation.

Each model *is* the parameter schema for its operation. It drives validation,
what lands in `boundary_op.parameters`, the generated CLI command, and the
`bounds show` rendering -- so the operation is defined once.

Each operation contributes a SQL **expression** wrapping the running geometry
rather than executing anything itself. `build.py` applies them one at a time
against a scratch row, so the geometry never leaves the database and a failure
is attributable to a single operation.

The geometry-bearing operations (`add`, `subtract`, `init`, `adopt`) are
authored in QGIS, which edits `map_bounds.boundary_op` directly as a PostGIS
layer. They are modelled here so that `show` and `build` understand them, but
they are not exposed as CLI commands.
"""

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from .units import Area, Distance

#: Operations permitted at position 0. Mirrors `boundary_op_opening_position`.
OPENING_OPERATIONS = ("union", "adopt", "init")


class BoundaryOp(BaseModel):
    """Base class for boundary operations."""

    #: Identifier, matching `map_bounds.boundary_operation.id`.
    op_id: ClassVar[str]
    #: Whether this operation carries an operand geometry.
    takes_geometry: ClassVar[bool] = False
    #: Whether QGIS (rather than the CLI) is the place to create it.
    geometry_authored: ClassVar[bool] = False

    model_config = {"extra": "forbid"}

    @property
    def description(self) -> str:
        return (self.__doc__ or "").strip().split("\n")[0]

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        """Wrap `inner` (SQL yielding a geometry) and return a new expression.

        `operand` is SQL yielding this row's `geometry` column, for the
        operations that carry one. Named parameters may be added to `params`.
        """
        raise NotImplementedError


# --------------------------------------------------------------------------
# Opening operations
# --------------------------------------------------------------------------


class Union(BoundaryOp):
    """Union the map's own features into a starting boundary."""

    op_id: ClassVar[str] = "union"
    takes_geometry: ClassVar[bool] = True  # caches its result

    srid: int = Field(4326, description="Working CRS for the union")
    approach: Literal["basic", "legacy", "naive"] = Field(
        "basic", description="Union algorithm"
    )

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        # `inner` is the cached geometry column for this row; recomputation is
        # handled by build.py under --init, not here.
        return inner


class Adopt(BoundaryOp):
    """Adopt a boundary shipped by the source dataset, without recomputation."""

    op_id: ClassVar[str] = "adopt"
    takes_geometry: ClassVar[bool] = True
    geometry_authored: ClassVar[bool] = True

    layer: str | None = Field(
        None, description="Source dataset layer the geometry came from"
    )

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        return inner


class Init(BoundaryOp):
    """Open the boundary with a hand-supplied geometry."""

    op_id: ClassVar[str] = "init"
    takes_geometry: ClassVar[bool] = True
    geometry_authored: ClassVar[bool] = True

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        return inner


# --------------------------------------------------------------------------
# Geometry-bearing modifiers -- authored in QGIS
# --------------------------------------------------------------------------


class Add(BoundaryOp):
    """Union an operand polygon into the boundary."""

    op_id: ClassVar[str] = "add"
    takes_geometry: ClassVar[bool] = True
    geometry_authored: ClassVar[bool] = True

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        return (
            "ST_Multi(ST_CollectionExtract(ST_MakeValid("
            f"ST_Union(ST_MakeValid({inner}), ST_MakeValid({operand}))), 3))"
        )


class Subtract(BoundaryOp):
    """Difference an operand polygon out of the boundary."""

    op_id: ClassVar[str] = "subtract"
    takes_geometry: ClassVar[bool] = True
    geometry_authored: ClassVar[bool] = True

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        return (
            "ST_Multi(ST_CollectionExtract(ST_MakeValid("
            f"ST_Difference(ST_MakeValid({inner}), ST_MakeValid({operand}))), 3))"
        )


# --------------------------------------------------------------------------
# Parameter-only modifiers -- these are the CLI surface
# --------------------------------------------------------------------------


class Buffer(BoundaryOp):
    """Dilate then erode, closing small gaps without growing the boundary."""

    op_id: ClassVar[str] = "buffer"

    distance: Distance = Field(
        ..., description="Gap size to close, e.g. 0.5km, 500m, 0.01deg"
    )

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        if self.distance.is_angular:
            params["buffer_dist"] = self.distance.degrees
            grow = f"ST_Buffer({inner}, :buffer_dist, 'endcap=round join=round')"
            return (
                "ST_Multi(ST_MakeValid("
                f"ST_Buffer({grow}, -:buffer_dist, 'endcap=flat join=mitre')"
                ", 'method=structure'))"
            )
        # Metric distances buffer on the geography type, matching basic.sql.
        params["buffer_dist"] = self.distance.meters
        grow = (
            f"ST_Buffer(({inner})::geography, :buffer_dist, "
            "'endcap=round join=round')::geometry"
        )
        return (
            "ST_Multi(ST_MakeValid("
            f"ST_Buffer(({grow})::geography, -:buffer_dist, "
            "'endcap=flat join=mitre')::geometry"
            ", 'method=structure'))"
        )


class FillHoles(BoundaryOp):
    """Drop interior rings, optionally only those below a maximum area."""

    op_id: ClassVar[str] = "fill_holes"

    max_area: Area | None = Field(
        None, description="Only fill holes below this area, e.g. 10km2"
    )

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        # ST_ExteriorRing returns NULL for a MULTIPOLYGON, so dump to parts and
        # rebuild each -- the same shape as basic.sql's fill step.
        if self.max_area is None:
            return (
                "(SELECT ST_Multi(ST_Union("
                "ST_MakePolygon(ST_ExteriorRing((d).geom))))"
                f" FROM ST_Dump({inner}) AS d)"
            )
        params["fill_max_area"] = self.max_area.square_meters
        # Rebuild each part keeping only interior rings above the threshold, so
        # small holes are filled and large ones survive.
        kept_rings = (
            "COALESCE((SELECT array_agg(rings.ring) FROM ("
            "  SELECT ST_InteriorRingN((d).geom, i) AS ring"
            "  FROM generate_series(1, ST_NumInteriorRings((d).geom)) AS i"
            " ) rings"
            " WHERE ST_Area(ST_MakePolygon(rings.ring)::geography)"
            " > :fill_max_area), ARRAY[]::geometry[])"
        )
        return (
            "(SELECT ST_Multi(ST_Union("
            f"ST_MakePolygon(ST_ExteriorRing((d).geom), {kept_rings})))"
            f" FROM ST_Dump({inner}) AS d)"
        )


class FixAntimeridian(BoundaryOp):
    """Split, shift and re-wrap geometry that spans the antimeridian."""

    op_id: ClassVar[str] = "fix_antimeridian"

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        meridian = "ST_GeomFromText('LINESTRING(180 -90, 180 90)', 4326)"
        g = f"ST_Segmentize(ST_MakeValid({inner})::geography, 10000)::geometry"
        g = f"ST_ShiftLongitude(ST_Split({g}, {meridian}))"
        g = f"ST_WrapX(ST_MakeValid(ST_Split({g}, {meridian})), 180, -360)"
        return f"ST_Multi(ST_CollectionExtract(ST_MakeValid({g}), 3))"


class ClipToWorld(BoundaryOp):
    """Intersect with the -180/-90..180/90 envelope."""

    op_id: ClassVar[str] = "clip_to_world"

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        return (
            "ST_Multi(ST_CollectionExtract(ST_Intersection("
            f"ST_MakeValid({inner}),"
            " ST_MakeEnvelope(-180, -90, 180, 90, 4326)), 3))"
        )


class Simplify(BoundaryOp):
    """Douglas-Peucker simplification, preserving topology."""

    op_id: ClassVar[str] = "simplify"

    tolerance: Distance = Field(..., description="Simplification tolerance, e.g. 100m")

    def sql(self, inner: str, params: dict[str, Any], operand: str) -> str:
        if self.tolerance.is_angular:
            params["simplify_tol"] = self.tolerance.degrees
        else:
            # ST_SimplifyPreserveTopology works in CRS units; approximate
            # metres as degrees at the equator, which is the conservative
            # direction (it simplifies less away from it).
            params["simplify_tol"] = self.tolerance.meters / 111_320.0
        return (
            "ST_Multi(ST_CollectionExtract(ST_MakeValid("
            f"ST_SimplifyPreserveTopology({inner}, :simplify_tol)), 3))"
        )


OPERATIONS: dict[str, type[BoundaryOp]] = {
    cls.op_id: cls
    for cls in (
        Union,
        Adopt,
        Init,
        Add,
        Subtract,
        Buffer,
        FillHoles,
        FixAntimeridian,
        ClipToWorld,
        Simplify,
    )
}

#: Operations the CLI can create: parameter-only, not authored in QGIS.
CLI_OPERATIONS = {
    k: v for k, v in OPERATIONS.items() if not v.geometry_authored and k != "union"
}


def load(operation: str, parameters: dict[str, Any] | None) -> BoundaryOp:
    """Rebuild a typed operation from a `boundary_op` row."""
    cls = OPERATIONS.get(operation)
    if cls is None:
        raise ValueError(f"Unknown boundary operation {operation!r}")
    # `parameters` is jsonb, so it can come back as any JSON value -- QGIS writes
    # an empty *string* rather than an empty object. Only a mapping carries
    # parameters; anything else means "none given".
    if not isinstance(parameters, dict):
        parameters = {}
    return cls.model_validate(parameters)
