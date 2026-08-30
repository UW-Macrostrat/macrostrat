"""Small unit-aware value types for boundary operation parameters.

Deliberately not `pint`: the vocabulary is three length units and one area unit,
and the values round-trip through `boundary_op.parameters` as JSON, so an
explicit `{value, unit}` pair is more legible in the database than a bare
canonical number.

Degrees are kept distinct from metric lengths rather than converted. A degree is
only ~111 km at the equator and shrinks with latitude, so a conversion would be
silently wrong for high-latitude maps. `basic.sql` already makes this
distinction -- it buffers on `::geography` (metres) when the working SRID is
4326 and planar otherwise -- and the SQL builders below preserve it.
"""

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema

LENGTH_UNITS = {"m": 1.0, "km": 1000.0}
AREA_UNITS = {"m2": 1.0, "km2": 1e6}

# The unit may carry a trailing digit (km2), so allow digits after the letters.
_QUANTITY = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z°]+\d*)\s*$")


def _parse(text: str, units: dict[str, float], what: str) -> tuple[float, str]:
    allowed = ", ".join(sorted(units))
    match = _QUANTITY.match(text)
    if match is None:
        raise ValueError(
            f"Could not read {what} from {text!r}; expected a number and one "
            f"of: {allowed}"
        )
    value, unit = float(match.group(1)), match.group(2)
    unit = {"°": "deg", "degrees": "deg", "degree": "deg"}.get(unit, unit)
    if unit not in units:
        raise ValueError(
            f"Unknown {what} unit {unit!r} in {text!r}; expected {allowed}"
        )
    return value, unit


class Distance(BaseModel):
    """A length, in metric units or in degrees of arc."""

    value: float
    unit: Literal["m", "km", "deg"]

    @classmethod
    def parse(cls, text: str) -> "Distance":
        value, unit = _parse(text, {**LENGTH_UNITS, "deg": 1.0}, "a distance")
        return cls(value=value, unit=unit)

    @property
    def is_angular(self) -> bool:
        return self.unit == "deg"

    @property
    def meters(self) -> float:
        if self.is_angular:
            raise ValueError(
                "This distance is in degrees and has no fixed length in metres"
            )
        return self.value * LENGTH_UNITS[self.unit]

    @property
    def degrees(self) -> float:
        if not self.is_angular:
            raise ValueError("This distance is metric, not angular")
        return self.value

    def __str__(self) -> str:
        return f"{self.value:g}{self.unit}"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Accept "0.5km" wherever a Distance is expected, in addition to the
        # {value, unit} form that comes back out of `parameters`.
        return core_schema.no_info_before_validator_function(
            lambda v: cls.parse(v) if isinstance(v, str) else v,
            handler(source),
        )


class Area(BaseModel):
    """An area, in metric units."""

    value: float
    unit: Literal["m2", "km2"]

    @classmethod
    def parse(cls, text: str) -> "Area":
        value, unit = _parse(text, AREA_UNITS, "an area")
        return cls(value=value, unit=unit)

    @property
    def square_meters(self) -> float:
        return self.value * AREA_UNITS[self.unit]

    def __str__(self) -> str:
        return f"{self.value:g}{self.unit}"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(
            lambda v: cls.parse(v) if isinstance(v, str) else v,
            handler(source),
        )


DistanceStr = Annotated[Distance, "e.g. 0.5km, 500m, 0.01deg"]
AreaStr = Annotated[Area, "e.g. 10km2"]
