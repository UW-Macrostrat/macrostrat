"""Macrostrat's column importer.

Build `Column` objects (with their `Section`s and `Unit`s) and write them with
`ingest_columns`, or ingest a workbook with `ingest_columns_from_file`. Import
from this package rather than from its submodules, which are reorganized freely.
The command-line app is `cli.app`.
"""

from importlib import import_module
from typing import TYPE_CHECKING

# Resolved on first access, so importing the package (as the CLI does) stays cheap
_EXPORTS = {
    "BoundaryStatus": ".boundary_status",
    "BoundaryType": ".boundary_type",
    "Column": ".columns",
    "ColumnReference": ".refs",
    "EnvironsProcessor": ".environs",
    "IngestValidationError": ".notices",
    "LithAbundance": ".lithologies",
    "LithsProcessor": ".lithologies",
    "Placement": ".ingest",
    "ProjectIdentifier": ".database",
    "Reference": ".refs",
    "RelativeAge": ".intervals",
    "Section": ".columns",
    "Unit": ".units",
    "UnknownEnvironError": ".environs",
    "get_interval_from_text": ".intervals",
    "get_intervals": ".intervals",
    "ingest_column_data": ".ingest",
    "ingest_columns": ".ingest",
    "ingest_columns_from_file": ".ingest",
}

__all__ = [*_EXPORTS, "notices"]


def __getattr__(name: str):
    if name == "notices":
        return import_module(".notices", __name__)
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_EXPORTS[name], __name__), name)
    globals()[name] = value
    return value


if TYPE_CHECKING:
    from . import notices
    from .boundary_status import BoundaryStatus
    from .boundary_type import BoundaryType
    from .columns import Column, Section
    from .database import ProjectIdentifier
    from .environs import EnvironsProcessor, UnknownEnvironError
    from .ingest import (
        Placement,
        ingest_column_data,
        ingest_columns,
        ingest_columns_from_file,
    )
    from .intervals import RelativeAge, get_interval_from_text, get_intervals
    from .lithologies import LithAbundance, LithsProcessor
    from .notices import IngestValidationError
    from .refs import ColumnReference, Reference
    from .units import Unit
