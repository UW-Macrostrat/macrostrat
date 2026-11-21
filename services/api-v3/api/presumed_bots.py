"""Presumed bots: automated tile traffic nobody identified at the time.

The harvester tags the clients it recognizes (`is_bot`). Sweeps it missed show
up as phases of traffic far above the long-term trend, and the overage during
such a phase is presumed automated. This runs over the whole archive on every
read, so a change to these rules is a change to every period.
"""

from bisect import bisect_left, bisect_right
from datetime import date

#: Days either side of each day that set its long-term trend.
TREND_HALF_WINDOW = 365
#: The trend is the mean of the days between these quantiles of the window.
TREND_BAND = (0.35, 0.65)
#: Days above this multiple of the trend are anomalous.
ANOMALY_RATIO = 2.0
#: Anomalous days this close together form one phase.
MAX_GAP_DAYS = 2
#: A phase counts only if some day in it reaches this multiple of the trend.
MIN_PEAK_RATIO = 5.0


def presumed_bots(days: list[date], counts: list[int]) -> list[int]:
    """Requests above the trend on each day of a bot phase, and 0 on other days.

    `days` are sorted and distinct. A day with no row is an outage.
    """
    ordinals = [d.toordinal() for d in days]
    trend = [_trend(ordinals, counts, i) for i in range(len(days))]
    presumed = [0] * len(days)
    for first, last in _phases(ordinals, counts, trend):
        peak = max(counts[i] / trend[i] for i in range(first, last + 1))
        if peak < MIN_PEAK_RATIO:
            continue
        for i in range(first, last + 1):
            presumed[i] = max(0, round(counts[i] - trend[i]))
    return presumed


def _trend(ordinals, counts, i) -> float:
    lo = bisect_left(ordinals, ordinals[i] - TREND_HALF_WINDOW)
    hi = bisect_right(ordinals, ordinals[i] + TREND_HALF_WINDOW)
    window = sorted(counts[lo:hi])
    start = int(TREND_BAND[0] * len(window))
    end = max(int(TREND_BAND[1] * len(window)), start + 1)
    band = window[start:end]
    # A zero trend would make any traffic infinitely anomalous.
    return max(sum(band) / len(band), 1)


def _phases(ordinals, counts, trend) -> list[tuple[int, int]]:
    """Index ranges of anomalous days, joined across short gaps."""
    anomalous = [i for i in range(len(counts)) if counts[i] > ANOMALY_RATIO * trend[i]]
    phases = []
    for i in anomalous:
        if phases and ordinals[i] - ordinals[phases[-1][1]] <= MAX_GAP_DAYS + 1:
            phases[-1][1] = i
        else:
            phases.append([i, i])
    return [(first, last) for first, last in phases]
