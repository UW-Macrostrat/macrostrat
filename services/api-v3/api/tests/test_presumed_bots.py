from datetime import date, timedelta

from api.presumed_bots import presumed_bots
from api.routes.usage_stats import _bin_days

START = date(2026, 1, 1)


def _days(n):
    return [START + timedelta(days=i) for i in range(n)]


def test_steady_traffic_has_no_bots():
    counts = [1000 + (i % 7) * 50 for i in range(200)]
    assert presumed_bots(_days(200), counts) == [0] * 200


def test_spike_excess_over_baseline():
    counts = [1000] * 100
    counts[50] = 5000
    presumed = presumed_bots(_days(100), counts)
    assert presumed[50] == 4000
    assert sum(presumed) == 4000


def test_months_long_sweep():
    counts = [1000] * 400
    for i in range(150, 300):
        counts[i] = 20_000
    presumed = presumed_bots(_days(400), counts)
    assert presumed[150:300] == [19_000] * 150
    assert sum(presumed) == 19_000 * 150


def test_outages_are_skipped():
    days = _days(60)
    del days[20:30]
    counts = [1000] * len(days)
    assert presumed_bots(days, counts) == [0] * len(days)


def test_weekly_bins_fill_gaps():
    days = [
        {
            "date": date(2026, 1, 5),
            "organic": 10,
            "bot": None,
            "presumed_bot": 2,
            "new_system": True,
        },
        {
            "date": date(2026, 1, 7),
            "organic": 5,
            "bot": 1,
            "presumed_bot": 0,
            "new_system": True,
        },
        {
            "date": date(2026, 1, 20),
            "organic": 3,
            "bot": None,
            "presumed_bot": 0,
            "new_system": True,
        },
    ]
    bins = _bin_days(days, "week")
    assert [b["date"] for b in bins] == [
        date(2026, 1, 5),
        date(2026, 1, 12),
        date(2026, 1, 19),
    ]
    assert bins[0] == {
        "date": date(2026, 1, 5),
        "organic": 15,
        "bot": 1,
        "presumed_bot": 2,
        "new_system": True,
    }
    assert bins[1] == {"date": date(2026, 1, 12)}


def test_monthly_bins():
    days = [
        {
            "date": date(2026, 1, 31),
            "organic": 1,
            "bot": None,
            "presumed_bot": 0,
            "new_system": False,
        },
        {
            "date": date(2026, 3, 1),
            "organic": 2,
            "bot": None,
            "presumed_bot": 0,
            "new_system": True,
        },
    ]
    assert [b["date"] for b in _bin_days(days, "month")] == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
    ]
