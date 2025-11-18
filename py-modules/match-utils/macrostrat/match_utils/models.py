from enum import Enum
from pandas import isna
from pydantic import BaseModel
from typing import Optional


class MatchResult(BaseModel):
    strat_name_id: int
    strat_name: str
    strat_rank: Optional[str]
    parent_id: Optional[int]
    concept_id: Optional[int]
    unit_id: Optional[int]
    col_id: Optional[int]
    depth: Optional[int]
    basis: str
    spatial_basis: str
    min_age: float
    max_age: float
    priority: float

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
