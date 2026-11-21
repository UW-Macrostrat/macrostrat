"""Presumed bots: automated tile traffic nobody identified at the time.

The harvester tags the clients it recognizes (`is_bot`). Sweeps it missed show
up only as days far above their neighbours, so each day is compared with a
local baseline and its excess on spike days is presumed automated. This runs
over the whole archive on every read, so a change to these rules is a change
to every period.
"""

from bisect import bisect_left, bisect_right
from datetime import date
from statistics import median

#: A day more than this many times its baseline is a spike.
SPIKE_RATIO = 1.5
#: A day's baseline is the median of this many nearest days that are not spikes.
BASELINE_DAYS = 28
#: Days either side of the first estimate; a months-long sweep stays a minority.
SEED_HALF_WINDOW = 182
#: The first estimate is low on purpose: later passes clear days it wrongly flags.
SEED_QUANTILE = 0.25
MAX_PASSES = 20


def presumed_bots(
    days: list[date],
    counts: list[int],
    *,
    spike_ratio: float = SPIKE_RATIO,
    baseline_days: int = BASELINE_DAYS,
) -> list[int]:
    """Requests above the baseline on each spike day, and 0 on other days.

    `days` are sorted and distinct. A day with no row is an outage, neither
    a spike nor part of any baseline.
    """
    ordinals = [d.toordinal() for d in days]
    baselines = [_seed(ordinals, counts, i) for i in range(len(days))]
    spikes = _spikes(counts, baselines, spike_ratio)
    # Excluding spikes lowers nearby baselines, which can expose more spikes.
    for _ in range(MAX_PASSES):
        baselines = [
            _nearest_median(ordinals, counts, spikes, i, baseline_days)
            for i in range(len(days))
        ]
        updated = _spikes(counts, baselines, spike_ratio)
        if updated == spikes:
            break
        spikes = updated
    return [
        round(count - base) if spike else 0
        for count, base, spike in zip(counts, baselines, spikes)
    ]


def _spikes(counts, baselines, ratio) -> list[bool]:
    return [count > ratio * base for count, base in zip(counts, baselines)]


def _seed(ordinals, counts, i) -> float:
    lo = bisect_left(ordinals, ordinals[i] - SEED_HALF_WINDOW)
    hi = bisect_right(ordinals, ordinals[i] + SEED_HALF_WINDOW)
    window = sorted(counts[lo:hi])
    return window[int(SEED_QUANTILE * (len(window) - 1))]


def _nearest_median(ordinals, counts, spikes, i, k) -> float:
    """Median of the `k` days nearest in time to day `i` that are not spikes."""
    values = []
    if not spikes[i]:
        values.append(counts[i])
    lo, hi = i - 1, i + 1
    while len(values) < k and (lo >= 0 or hi < len(ordinals)):
        take_lo = hi >= len(ordinals) or (
            lo >= 0 and ordinals[i] - ordinals[lo] <= ordinals[hi] - ordinals[i]
        )
        if take_lo:
            j, lo = lo, lo - 1
        else:
            j, hi = hi, hi + 1
        if not spikes[j]:
            values.append(counts[j])
    if not values:
        return counts[i]
    return median(values)
