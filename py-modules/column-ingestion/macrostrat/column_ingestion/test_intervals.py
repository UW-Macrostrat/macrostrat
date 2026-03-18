"""Test cases for intervals matching"""

from dataclasses import dataclass
from pytest import mark
from .database import get_all_intervals


def get_intervals():
    return [
        Interval(row.id, row.interval_name, row.age_bottom, row.age_top)
        for row in get_all_intervals()
    ]


def test_get_intervals():
    """Test that get_all_intervals returns the correct intervals"""
    intervals = get_intervals()
    assert len(intervals) > 0


@dataclass
class IntervalID:
    id: int
    name: str

    def __hash__(self):
        return hash(self.id, self.name)


@dataclass
class Interval:
    id: int
    name: str
    age_bottom: float
    age_top: float

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name


test_text = "Early Cambrian, Series 2, Stage 3"


@dataclass
class IntervalTestCase:
    text: str
    expected: IntervalID


test_cases = [
    IntervalTestCase(
        "Early Cambrian, Series 2, Stage 3", IntervalID(id=254, name="Stage 3")
    ),
    IntervalTestCase(
        "Early Cambrian, Series 2, Stage 4", IntervalID(id=253, name="Stage 4")
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
    all_intervals = get_intervals()

    split_text = test_case.text.split(",")
    ints = []
    for _int in split_text:
        a = _int.strip()
        # Find the interval that matches the most
        match = [i for i in all_intervals if i.name == a]
        if match:
            ints.append(match[0])
        else:
            print(f"No match for {a}")

    # Order by age range descending
    ints.sort(key=lambda i: (i.age_bottom - i.age_top), reverse=True)
    # Ensure that intervals all overlap
    last_int = ints[-1]
    for _int in ints[:-1]:
        assert _int.age_bottom >= last_int.age_top
        assert _int.age_top <= last_int.age_bottom
    assert last_int == test_case.expected
