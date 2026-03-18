"""Test cases for intervals matching"""

from dataclasses import dataclass

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


def test_most_specific_interval():
    # Test that all intervals are matched and return the most specific
    res = IntervalID(name="Stage 3", id=254)
    all_intervals = get_intervals()

    split_text = test_text.split(",")
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
    age_bottom = 4500
    age_top = 0
    last_int = ints[-1]
    for _int in ints[:-1]:
        assert _int.age_bottom >= last_int.age_top
        assert _int.age_top <= last_int.age_bottom
    assert last_int == res
