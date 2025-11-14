from enum import Enum
from pandas import isna

from .clean_strat_name import format_name


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


def format_names(strat_names, **kwargs):
    # Ignore nan values
    if isna(strat_names):
        return strat_names
    # if it's already a string, return it
    if isinstance(strat_names, str):
        return strat_names

    return ", ".join([format_name(i, **kwargs) for i in strat_names])
