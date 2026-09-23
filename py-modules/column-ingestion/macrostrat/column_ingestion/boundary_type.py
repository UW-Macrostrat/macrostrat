"""The geological character of a surface between units.

Mirrors `macrostrat.boundary_type`, the enum behind `unit_boundaries.boundary_type`,
including its empty member. Kept apart from `boundary_status`, which records where a
boundary's *age* came from; this records what the boundary *is*.
"""

from enum import Enum


class BoundaryType(str, Enum):
    UNSPECIFIED = ""
    UNCONFORMITY = "unconformity"
    CONFORMITY = "conformity"
    FAULT = "fault"
    DISCONFORMITY = "disconformity"
    NON_CONFORMITY = "non-conformity"
    ANGULAR_UNCONFORMITY = "angular unconformity"


#: Boundaries across which stratigraphy is not continuous. A unit whose base is one of
#: these opens a new section — see `columns.sections.split_at_gaps`.
NON_CONFORMABLE = frozenset(
    {
        BoundaryType.UNCONFORMITY,
        BoundaryType.FAULT,
        BoundaryType.DISCONFORMITY,
        BoundaryType.NON_CONFORMITY,
        BoundaryType.ANGULAR_UNCONFORMITY,
    }
)
