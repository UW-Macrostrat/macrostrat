"""Ordering of the (b_interval, t_interval) pair returned for a free-text age.

Which of two intervals is the base is a fact about the timescale, not about word
order -- NGS writes ranges both oldest-first and youngest-first, so the pair has
to be ordered by age. Every string here appears in `sources.ngs_polygons`.
"""

import pytest

from macrostrat.map_integration.utils.gems_utils import lookup_and_validate_age

# A miniature timescale, ages in Ma: id -> (name, age_bottom, age_top).
_INTERVALS = {
    1: ("holocene", 0.0117, 0.0),
    2: ("pleistocene", 2.58, 0.0117),
    3: ("quaternary", 2.58, 0.0),
    4: ("miocene", 23.03, 5.333),
    5: ("pliocene", 5.333, 2.58),
    6: ("cambrian", 538.8, 486.85),
    7: ("ordovician", 486.85, 443.1),
    8: ("early cretaceous", 145.0, 100.5),
    9: ("late cretaceous", 100.5, 66.0),
}

LOOKUP = {name: i for i, (name, _, _) in _INTERVALS.items()}
AGES = {i: (bottom, top) for i, (_, bottom, top) in _INTERVALS.items()}


@pytest.mark.parametrize(
    "text,base,top",
    [
        # A conjunction used to collapse to the first interval named, twice over.
        ("holocene and pleistocene", "pleistocene", "holocene"),
        # ...and the answer must not depend on which way round it is written.
        ("pleistocene and holocene", "pleistocene", "holocene"),
        ("holocene or pleistocene", "pleistocene", "holocene"),
        ("holocene to pleistocene", "pleistocene", "holocene"),
        ("holocene and/or pleistocene", "pleistocene", "holocene"),
        ("cambrian-ordovician", "cambrian", "ordovician"),
        ("ordovician-cambrian", "cambrian", "ordovician"),
        ("pliocene and miocene", "miocene", "pliocene"),
        ("late cretaceous to early cretaceous", "early cretaceous", "late cretaceous"),
        # One interval named fills both slots.
        ("quaternary", "quaternary", "quaternary"),
        # `upper`/`lower` are qualifiers for `late`/`early`.
        ("upper cretaceous", "late cretaceous", "late cretaceous"),
    ],
)
def test_pair_is_ordered_by_age(text, base, top):
    b, t = lookup_and_validate_age(text, LOOKUP, AGES)
    assert (LOOKUP[base], LOOKUP[top]) == (b, t)


@pytest.mark.parametrize("text", ["modern", "unknown", "17-6 ma", "last glaciation"])
def test_unresolvable_ages_are_left_null(text):
    b, t = lookup_and_validate_age(text, LOOKUP, AGES)
    assert b is not None and t is not None  # pandas NA, not None
    assert str(b) == "<NA>" and str(t) == "<NA>"


def test_without_ages_the_pair_is_left_as_found():
    """The historical behaviour, for a caller that has no ages to compare."""
    b, t = lookup_and_validate_age("cambrian-ordovician", LOOKUP)
    assert (b, t) == (LOOKUP["cambrian"], LOOKUP["ordovician"])
