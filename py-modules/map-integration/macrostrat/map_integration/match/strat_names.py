"""Match a map source's legend text to Macrostrat's stratigraphic lexicon.

This replaces twelve additive SQL passes that wrote roughly nine copies of every
fact they found -- 22,304,055 rows expressing 64,897 facts across the whole maps
schema. The comparison now happens in Python over a blocked candidate set, once
per legend entry, and the result is written once at legend grain into
`maps.legend_strat_names`.

The matcher itself is `strat_names_v2`, which carries the reasoning for each
rule it applies. See [[Map geologic name matching]] for how it was measured.
"""

import time

from rich import print

from ..database import get_database
from ..utils import MapInfo
from .strat_names_v2 import LocationBasis, match_source, prepare, write_matches


def match_strat_names(map: MapInfo):
    """Match this source's legend to the lexicon and record the result."""
    db = get_database()
    match_strat_names_for_source(db, map.slug)


def match_strat_names_for_source(db, slug: str) -> int:
    start = time.time()
    print(f"      Matching strat names for [bold cyan]{slug}[/]")

    lexicon = prepare(db)
    matches = match_source(db, slug, lexicon)
    written = write_matches(db, slug, matches)

    by_basis = {}
    for m in matches:
        by_basis[m.location_basis] = by_basis.get(m.location_basis, 0) + 1
    summary = "  ".join(
        f"{basis.value}={by_basis[basis]}"
        for basis in LocationBasis
        if basis in by_basis
    )
    print(
        f"        Matched [bold cyan]{written}[/] strat names in {time.time() - start:.1f}s"
    )
    if summary:
        print(f"        {summary}")
    return written
