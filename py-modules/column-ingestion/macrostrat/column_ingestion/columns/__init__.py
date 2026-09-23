"""Columns: reading them out of a workbook, and writing them with their sections.

- `parse` — spreadsheet rows to `Column` objects, and the units sheet to each column's
  sections of units.
- `geometry` — resolving lat/lng or polygon WKT into everything `cols` needs, via PostGIS.
- `sections` — the `Section` model, the strategies for deriving sections where a source
  has none, and their reconciliation ahead of the units that reference them.
- `writer` — column groups and columns, reconciled rather than replaced.
"""

from .geometry import ColumnGeometry, GeometryError, resolve_geometry
from .parse import Column, get_column_data, get_sections, get_sections_from_df
from .sections import (
    Section,
    ordered_sections,
    reconcile_sections,
    section_bounds,
    section_identity,
    single_section,
    split_at_gaps,
    stacking_direction,
)
from .writer import reconcile_column_group, reconcile_columns

__all__ = [
    "Column",
    "ColumnGeometry",
    "GeometryError",
    "Section",
    "get_column_data",
    "get_sections",
    "get_sections_from_df",
    "ordered_sections",
    "reconcile_column_group",
    "reconcile_columns",
    "reconcile_sections",
    "resolve_geometry",
    "section_bounds",
    "section_identity",
    "single_section",
    "split_at_gaps",
    "stacking_direction",
]
