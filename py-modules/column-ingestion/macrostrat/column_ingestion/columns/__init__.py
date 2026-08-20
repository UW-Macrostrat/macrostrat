"""Columns: reading them out of a workbook, and writing them with their sections.

- `parse` — spreadsheet rows to `Column` objects.
- `geometry` — resolving lat/lng or polygon WKT into everything `cols` needs, via PostGIS.
- `sections` — a column's sections, created before the units that reference them.
- `writer` — column groups and columns, reconciled rather than replaced.
"""

from .geometry import ColumnGeometry, GeometryError, resolve_geometry
from .parse import Column, get_column_data
from .sections import (
    assign_section_ids,
    group_units_by_section,
    reconcile_sections,
    section_bounds,
)
from .writer import reconcile_column_group, reconcile_columns

__all__ = [
    "Column",
    "ColumnGeometry",
    "GeometryError",
    "assign_section_ids",
    "get_column_data",
    "group_units_by_section",
    "reconcile_column_group",
    "reconcile_columns",
    "reconcile_sections",
    "resolve_geometry",
    "section_bounds",
]
