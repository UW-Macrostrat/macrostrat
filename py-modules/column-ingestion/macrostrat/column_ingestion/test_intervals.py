"""Test cases for intervals matching"""

from dataclasses import dataclass
from pytest import mark

from .intervals import IntervalID, get_intervals, get_interval_from_text


def test_get_intervals():
    """Test that get_all_intervals returns the correct intervals"""
    intervals = get_intervals()
    assert len(intervals) > 0


@dataclass
class IntervalTestCase:
    text: str
    expected: IntervalID


test_cases = [
    IntervalTestCase(
        "254",
        IntervalID(id=254, name="Stage 3"),
    ),
    IntervalTestCase("Early Cambrian, 254", IntervalID(id=254, name="Stage 3")),
    IntervalTestCase(
        "Early Cambrian, Series 2, 254", IntervalID(id=254, name="Stage 3")
    ),
    IntervalTestCase(
        "Early Cambrian, Series 2, Stage 3", IntervalID(id=254, name="Stage 3")
    ),
    IntervalTestCase(
        "Early Cambrian, Series 2, Stage 4", IntervalID(id=253, name="Stage 4")
    ),
    IntervalTestCase(
        "Early Cambrian > Series 2 > Stage 4", IntervalID(id=253, name="Stage 4")
    ),
    IntervalTestCase(
        "Early Cambrian, Tommotian", IntervalID(id=1690, name="Tommotian")
    ),
    IntervalTestCase("Early Cambrian", IntervalID(id=130, name="Early Cambrian")),
    IntervalTestCase("Series 2", IntervalID(id=501, name="Series 2")),
    IntervalTestCase("Olenellus", IntervalID(id=520, name="Olenellus")),
]


@mark.parametrize("test_case", test_cases)
def test_get_interval(test_case: IntervalTestCase):
    # Test that all intervals are matched and return the most specific
    assert get_interval_from_text(test_case.text) == test_case.expected
