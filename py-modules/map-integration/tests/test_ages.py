"""Resolving numeric ages and interval pairs, against a miniature timescale."""

import pytest

from macrostrat.map_integration.ages import (
    Interval,
    interval_for_age,
    numeric_range,
    span,
    spanning_interval,
)

_ROWS = [
    (1, "Meghalayan", 0.0042, 0.0),
    (2, "Gelasian", 2.58, 1.8),
    (3, "Calabrian", 1.8, 0.774),
    (4, "Chibanian", 0.774, 0.129),
    (5, "Upper Pleistocene", 0.129, 0.0117),
    (6, "Greenlandian", 0.0117, 0.0082),
    (7, "Northgrippian", 0.0082, 0.0042),
    (8, "Quaternary", 2.58, 0.0),
    (9, "Tonian", 1000.0, 720.0),
    (10, "Cryogenian", 720.0, 635.0),
    (11, "Ediacaran", 635.0, 538.8),
    (12, "Neoproterozoic", 1000.0, 538.8),
    (13, "Stenian", 1200.0, 1000.0),
    (14, "Proterozoic", 2500.0, 538.8),
]
INTERVALS = [Interval(*r) for r in _ROWS]
BY_NAME = {i.name: i for i in INTERVALS}


@pytest.mark.parametrize(
    "age,base,expected",
    [
        (575.0, True, "Ediacaran"),
        # A boundary age is the base of the younger interval...
        (1000.0, True, "Tonian"),
        # ...and the top of the older one.
        (1000.0, False, "Stenian"),
        (538.8, False, "Ediacaran"),
        (0.0, False, "Meghalayan"),
        (0.0, True, None),
    ],
)
def test_interval_for_age(age, base, expected):
    found = interval_for_age(age, INTERVALS, base=base)
    assert (found.name if found else None) == expected


def test_span_orders_by_age_not_position():
    pairs = [
        (BY_NAME["Cryogenian"], BY_NAME["Ediacaran"]),
        (BY_NAME["Tonian"], BY_NAME["Tonian"]),
    ]
    b, t = span(pairs)
    assert (b.name, t.name) == ("Tonian", "Ediacaran")


@pytest.mark.parametrize(
    "b,t,expected",
    [
        ("Gelasian", "Meghalayan", "Quaternary"),
        ("Tonian", "Ediacaran", "Neoproterozoic"),
        ("Calabrian", "Meghalayan", None),
        ("Tonian", "Tonian", None),
    ],
)
def test_spanning_interval(b, t, expected):
    found = spanning_interval(BY_NAME[b], BY_NAME[t], INTERVALS)
    assert (found.name if found else None) == expected


@pytest.mark.parametrize(
    "base,top,expected",
    [
        (2.58, 0.0, ("Quaternary", "Quaternary")),
        (1000.0, 538.8, ("Neoproterozoic", "Neoproterozoic")),
        (555.0, 549.0, ("Ediacaran", "Ediacaran")),
        (1.8, 0.0, ("Calabrian", "Meghalayan")),
    ],
)
def test_numeric_range(base, top, expected):
    b, t = numeric_range(base, top, INTERVALS)
    assert (b.name, t.name) == expected
