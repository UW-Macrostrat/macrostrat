"""Recover age-model constraints from the legacy `fo`/`lo` unit fields.

An eODP-specific importer to recover age-model constraints from `fo`/`lo` fields.
Most Macrostrat columns record age control directly in
`unit_boundaries` as `relative` boundaries; a large set of ocean-drilling columns
instead use on `units.fo` / `units.lo` (`fo == lo` throughout, `fo_h`/`lo_h`
unused).

Here, the work is split in two:

1. **Here** — turn `fo`/`lo` into a small set of *relative* age constraints. This
   is where the eODP-specific decisions are, and it is only ~11% of the
   boundaries in a section.
2. **`age_model.AgeModel`** — fill in every remaining surface by the ordinary
   interpolation, marking them `modeled`.

There are two things that are currently treated as special cases for eODP

- The imposed proportions show up in the database as a handful of `relative` boundaries.
- Position is summed on cumulative thickness, irrespective of overlaps or gaps. This is a
  limitation of the model that we should revisit in the future (see `EODPAgeModel.axis_position`).

Note also that boundaries take the `fo` of the unit **below** it. So for a run of units
  sharing an interval ("package"), the boundaries carrying that interval are the
  ones at the *top* of each of its units.
"""

from dataclasses import dataclass

from macrostrat.utils import get_logger

from ..intervals import Interval, RelativeAge, get_interval_by_id
from ..units import Unit
from .model import AgeModel, AgeModelSurface, BoundaryStatus
from .reconciliation import BoundaryPlan, reconcile_unit_boundaries

log = get_logger(__name__)

#: How far each boundary in a section's **oldest** interval is moved toward the top of that
#: interval. The legacy generator spells this `bottom_offset = 3/2` and applies
#: `(1 - p)/1.5 + p`, which is the same thing: close two thirds of the gap to `prop = 1`.
OLDEST_INTERVAL_COMPRESSION = 2 / 3


def compress_toward_interval_top(proportion: float) -> float:
    """Move a proportion ~two thirds of the way toward the top of its interval.

    **Assumption:** reaching an interval at the bottom of a hole does not mean
    sampling all of it.  the whole of the section's oldest interval is squeezed into the
    top third of its duration. This is adjusted based on the depositional rate
    above the bottom interval.
    """
    return proportion + OLDEST_INTERVAL_COMPRESSION * (1 - proportion)


@dataclass
class EODPPackage:
    """A set of consecutive units sharing the same `fo` interval.

    `first` and `last` are 1-based unit indices, inclusive, ordered top (young)
    to bottom (old) — matching the boundary indexing described in
    `eodp_surfaces`.
    """

    interval: Interval
    first: int
    last: int

    @property
    def n_units(self) -> int:
        return self.last - self.first + 1


def cumulative_thickness(units: list[Unit]) -> list[float]:
    """Cumulative unit thickness, ignoring gaps and overlaps between units.

    Returns `n + 1` values: `C[0] == 0`, and `C[i]` is the total thickness of
    units 1..i. `C[i]` is the interpolation coordinate of boundary `i`.
    """
    coords = [0.0]
    for unit in units:
        coords.append(coords[-1] + abs(float(unit.b_pos) - float(unit.t_pos)))
    return coords


def package_interval(unit: Unit) -> Interval:
    """The interval a unit contributes to a package, and that its top boundary carries.

    **`lo`, not `fo`.** The generator groups units by `u.lo` and gives each boundary
    `t1 = <that lo interval>`; our original decode said `fo`, which agrees for the 89% of
    units where `fo = lo` but not for the other 14,940. `lo` is what the code does.

    `lo` arrives on the unit as `t_age` — see `eodp_units`.
    """
    return unit.t_age.interval


def group_packages(units: list[Unit]) -> list[EODPPackage]:
    """Split units into maximal runs sharing the same `lo` interval."""
    packages = []
    start = 0
    for i in range(1, len(units) + 1):
        if i == len(units) or package_interval(units[i]) != package_interval(
            units[start]
        ):
            packages.append(EODPPackage(package_interval(units[start]), start + 1, i))
            start = i
    return packages


def _package_anchors(
    package: EODPPackage, coords: list[float], *, is_first: bool
) -> tuple[float, float]:
    """Thickness coordinates at which the package's interval starts and ends.

    The generator divides an interval's age span across a denominator of

        (thickness of the units in the package) + (thickness of the unit above it)

    which in cumulative-thickness terms is the range `C[first-2] .. C[last]` — the
    boundaries bracketing the run that carries the interval. So an interval is stretched
    one boundary wider on each side than the boundaries it actually dates, and none of them
    lands exactly on its own interval's limit.

    The first package looks like a special case but is not. Its "unit above" is the
    section's top unit, which is *also* a member of the package, so that unit's thickness
    is counted **twice** — once in the package sum and once as the unit above. Hence the
    `+ (coords[1] - coords[0])` below. This was previously described here as an off-by-one
    in the original code; it is not, it falls straight out of the same denominator.
    """
    k, m = package.first, package.last

    if is_first:
        # The unit above the first package is its own first unit, so its thickness lands in
        # the denominator twice. See the docstring — this is the same rule, not an
        # exception to it.
        return coords[0], coords[m] + (coords[1] - coords[0])
    return coords[k - 2], coords[m]


def eodp_surfaces(units: list[Unit]) -> list[AgeModelSurface]:
    """Build the age-model surfaces for a section, constraining only a few.

    `units` are ordered by `position_bottom` ascending and carry their
    `fo` interval on `b_age`.

    Only the surfaces this module can actually justify get a `relative_age`: the first and
    last carrying boundary of each package, plus the base of the hole. Everything between
    them is filled in by the age model's ordinary interpolation.

    Boundaries carrying the section's **oldest** interval are additionally compressed toward
    the top of that interval — see `compress_toward_interval_top` for the assumption that
    encodes.
    """
    if not units:
        return []

    coords = cumulative_thickness(units)
    packages = group_packages(units)
    n = len(units)

    # The section's oldest interval — the generator calls it `section_fo` — is the one whose
    # boundaries get compressed toward its top. It is normally the last package, but take it
    # by age rather than by position so an out-of-order section still picks the right one.
    oldest = max(packages, key=lambda p: p.interval.age_bottom).interval

    constraints: dict[int, RelativeAge] = {}
    for index, package in enumerate(packages):
        is_last = index == len(packages) - 1
        top, bottom = _package_anchors(package, coords, is_first=index == 0)
        span = bottom - top
        if span <= 0:
            log.warning(
                "Section %s: package %s has no thickness; skipping constraints",
                units[0].section_id,
                package.interval.name,
            )
            continue

        # Boundaries carrying this package's interval sit at the top of each of its units.
        # The last package also carries the base of the hole, where the accumulation runs
        # out — proportion 0 before compression.
        carried = list(range(package.first - 1, package.last))
        if is_last:
            carried.append(package.last)

        # Constrain only the endpoints — the rest are collinear with them, and compression
        # is affine so it preserves that.
        for i in {carried[0], carried[-1]}:
            proportion = (bottom - coords[i]) / span
            if package.interval == oldest:
                proportion = compress_toward_interval_top(proportion)
            constraints[i] = RelativeAge(package.interval, proportion)

    surfaces = []
    for i in range(n + 1):
        above = [units[i - 1]] if i >= 1 else []
        below = [units[i]] if i < n else []
        position = float(units[0].t_pos) if i == 0 else float(units[i - 1].b_pos)
        surfaces.append(
            AgeModelSurface(
                position=position,
                units=[],
                boundary_status=BoundaryStatus.MODELED,
                relative_age=constraints.get(i),
                above=above,
                below=below,
                # Constraints here are per-package, not per-unit; anything this
                # module did not constrain is for the age model to fill in.
                infer_relative_age=False,
            )
        )
    return surfaces


class EODPAgeModel(AgeModel):
    """The general age model, spreading time along recovered thickness.

    Everything eODP-specific about *filling in* ages is this one override. The
    constraints themselves come from `eodp_surfaces`.

    This encodes an eODP-specific assumption about how to treat non-recovered core.
    The eODP importer interpolates across cumulative thickness rather than measured
    depth. This reflects instability at the margin of core recovery, where missing
    core or (in some cases) core double-counted in the height domain would otherwise
    produce a non-monotonic age model.
    """

    def __init__(
        self, db, surfaces: list[AgeModelSurface], units: list[Unit], **kwargs
    ):
        # Cumulative thickness through each unit, keyed by the unit above the
        # surface — each surface sits at the bottom of exactly one unit, except
        # the topmost, which has nothing above it and sits at zero.
        coords = cumulative_thickness(units)
        self._thickness = {unit.id: coords[i + 1] for i, unit in enumerate(units)}
        super().__init__(db, surfaces, **kwargs)

    def axis_position(self, surface: AgeModelSurface) -> float:
        above = surface.units_above
        if not above:
            return 0.0
        return self._thickness[above[0].id]


def eodp_units(db, section_id: int) -> list[Unit]:
    """Load a section's units with their `fo`/`lo` intervals attached.

    `fo` becomes `b_age` (proportion 0 — the base of the interval) and `lo`
    becomes `t_age` (proportion 1 — its top), which is what those fields mean.
    `eodp_surfaces` only reads the interval off `b_age`; the proportions are
    set for consistency with how `units.get_units_from_df` populates them.

    Ordered by `position_bottom` — see `eodp_surfaces` on why that matters.

    Membership comes from **`units_sections`**, which is authoritative. Neither
    `units.col_id` nor `units.section_id` is: they diverge from the join table for 259 and
    5,237 links respectively, and going through `units.section_id` leaves **306 eODP
    sections invisible** (1,723 reachable versus 2,029). Those columns are for creating
    units, not for retrieving them.
    """
    rows = db.run_query(
        """
        SELECT u.id, us.col_id, us.section_id, u.position_top, u.position_bottom,
               u.fo, u.lo, u.fo_h, u.lo_h
        FROM macrostrat.units u
        JOIN macrostrat.units_sections us ON us.unit_id = u.id
        WHERE us.section_id = :section_id
        ORDER BY u.position_bottom
        """,
        dict(section_id=section_id),
    ).fetchall()

    graded = [r.id for r in rows if (r.fo_h or 0) != 0 or (r.lo_h or 0) != 0]
    if graded:
        # `fo_h`/`lo_h` are bin ordinals naming which slice of an interval a unit occupies,
        # and they drive the *other* legacy generator — the interval model. All 92,451 eODP
        # units carry zero, which is exactly why eODP needed a thickness model. A non-zero
        # value means the column was not built this way and this decoder does not describe
        # it.
        log.warning(
            "Section %s: %s unit(s) carry a non-zero fo_h/lo_h (e.g. %s). Those are "
            "interval-model bin ordinals, so this thickness decoder probably does not "
            "apply to this column.",
            section_id,
            len(graded),
            graded[:5],
        )

    units = []
    for row in rows:
        if row.fo != row.lo:
            log.warning(
                "Unit %s has fo != lo (%s != %s); these should match for consistency",
                row.id,
                row.fo,
                row.lo,
            )
        unit = Unit(
            id=row.id,
            col_id=row.col_id,
            section_id=row.section_id,
            t_pos=float(row.position_top),
            b_pos=float(row.position_bottom),
        )
        unit.b_age = RelativeAge(get_interval_by_id(db, row.fo), 0)
        unit.t_age = RelativeAge(get_interval_by_id(db, row.lo), 1)
        units.append(unit)
    return units


def build_eodp_section_age_model(
    db, section_id: int, *, dry_run: bool = False
) -> BoundaryPlan | None:
    """Rebuild a section's `unit_boundaries` from its legacy `fo`/`lo` fields.

    Stage 1 derives the eODP-specific constraints, stage 2 (`AgeModel`) fills in
    the rest. The constrained surfaces land in the database as `relative`
    boundaries and the interpolated ones as `modeled`, so which ages came from the
    legacy hack is visible in the data.

    Returns the reconciliation plan, or `None` if the section could not be modeled.
    `dry_run=True` plans and logs without writing.
    """
    from .model import create_unit_boundaries

    units = eodp_units(db, section_id)
    surfaces = eodp_surfaces(units)
    if not surfaces:
        log.warning("Section %s has no units", section_id)
        return None

    model = EODPAgeModel(db, surfaces, units)
    if not model.has_valid_age_model:
        log.warning(
            "Section %s: fewer than two distinct age constraints; not modeling",
            section_id,
        )
        return None

    boundaries = list(create_unit_boundaries(model.apply()))

    with db.transaction():
        return reconcile_unit_boundaries(db, section_id, boundaries, dry_run=dry_run)


def build_eodp_age_model_for_existing_column(
    db, col_id: int, *, dry_run: bool = False
) -> dict[int, BoundaryPlan]:
    """Rebuild every section of an eODP column from its `fo`/`lo` fields.

    Mirrors `model.build_age_model_for_existing_column`, so the two approaches are
    interchangeable from a caller's point of view — see `approaches`.
    """
    section_ids = [
        row.id
        for row in db.run_query(
            """
            SELECT id FROM macrostrat.sections
            WHERE col_id = :col_id ORDER BY id
            """,
            dict(col_id=col_id),
        )
    ]
    if not section_ids:
        log.warning("Column %s has no sections", col_id)

    plans = {}
    for section_id in section_ids:
        plan = build_eodp_section_age_model(db, section_id, dry_run=dry_run)
        if plan is not None:
            plans[section_id] = plan
    return plans
