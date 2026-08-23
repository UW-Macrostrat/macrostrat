"""Provenance of a boundary's age control.

Its own module because both `units` and `age_model` need it, and `age_model`
already imports `units` — putting it in either would make that cycle.
"""

from enum import Enum


class BoundaryStatus(Enum):
    """Where a boundary's age control came from.

    Every value here except `ABSOLUTE` is stored the same way — an interval plus a
    proportion through it — and `unit_boundaries` keeps `(t1, t1_prop, t1_age)` for
    all of them. The status records *provenance*, not storage, with one exception
    that matters: `rebuild/sql/unit-boundaries.sql` branches on `ABSOLUTE` to decide
    which field is authoritative. For `ABSOLUTE` the age wins and the proportion is
    recomputed from it; for everything else interval + proportion win and the age is
    recomputed from them.

    - `MODELED` — interpolated by this age model between other constraints.
    - `RELATIVE` — the source stated a position within a named interval.
    - `ABSOLUTE` — the source stated a number, and that number is authoritative.
    - `SPIKE` — a GSSP.
    - `IMPOSED` — the source gave no chronostratigraphic anchor at all, and the age
      was derived by interpolating through thickness. **An imposed boundary is still
      stored relative to an interval**; the status records only that its proportion
      came from stratigraphic thickness rather than from a dated tie. The
      consequence to accept knowingly is that its age moves if the timescale is
      revised — the same tradeoff `RELATIVE` already makes.
    """

    MODELED = "modeled"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"
    SPIKE = "spike"
    IMPOSED = "imposed"
