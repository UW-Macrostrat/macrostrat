from enum import Enum
from typing import Optional

from pandas import isna
from pydantic import BaseModel, model_validator


class MatchResult(BaseModel):
    strat_name_id: int
    strat_name: str
    strat_rank: Optional[str]
    parent_id: Optional[int]
    concept_id: Optional[int]
    unit_id: Optional[int]
    col_id: Optional[int]
    project_id: Optional[int]
    depth: Optional[int]
    basis: str
    spatial_basis: str
    min_age: float
    max_age: float
    priority: float

    # TODO: refs
    # Provide more match information with a response="detailed" option

    @model_validator(mode="after")
    def check_column_project(self):
        """Ensure that project_id is set if col_id is set."""
        if self.col_id is not None and self.project_id is None:
            raise ValueError("project_id must be set if col_id is set.")
        return self

    @classmethod
    def from_row(cls, row):
        """Create a MatchResult from a pandas Series row."""
        vals = dict(row)
        for key, val in vals.items():
            if isna(val):
                vals[key] = None
        return cls(**vals)


class MatchType(Enum):
    Concepts = "concepts"
    AdjacentCols = "adjacent-cols"
    ColumnUnits = "column-units"
    FootprintIndex = "footprint-index"
    Synonyms = "synonyms"


class MatchComparison(Enum):
    Exact = "exact"
    Included = "included"
    Bidirectional = "bidirectional"
    Fuzzy = "fuzzy"
