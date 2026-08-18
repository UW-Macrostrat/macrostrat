"""Recover age-model constraints from the legacy `fo`/`lo` unit fields.

An eODP-specific importer to recover age-model constraints from `fo`/`lo` fields.
Most Macrostrat columns record age control directly in
`unit_boundaries` as `relative` boundaries; a large set of ocean-drilling columns
instead use on `units.fo` / `units.lo` (`fo == lo` throughout, `fo_h`/`lo_h`
unused).

Here, the work is split in two:

1. **Here** — turn `fo`/`lo` into a small set of *relative* age constraints. This
   is where every eODP-specific quirk lives, and it is only ~11% of the
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

#: The base of the hole is unconstrained — it is where drilling stopped, not a
#: dated surface. The eODP importer hedges by placing it one third of the way
#: into its interval's duration.
BASAL_PROPORTION = 2 / 3


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


def group_packages(units: list[Unit]) -> list[EODPPackage]:
    """Split units into maximal runs sharing the same `fo` interval."""
    packages = []
    start = 0
    for i in range(1, len(units) + 1):
        if i == len(units) or units[i].b_age.interval != units[start].b_age.interval:
            packages.append(EODPPackage(units[start].b_age.interval, start + 1, i))
            start = i
    return packages


def _package_anchors(
    package: EODPPackage,
    coords: list[float],
    *,
    is_first: bool,
    is_last: bool,
) -> tuple[float, float]:
    """Thickness coordinates at which the package's interval starts and ends.

    The interval's age span is anchored on the two boundaries that *bracket* the
    run of boundaries carrying it: `age_top` at boundary `first - 2`, `age_bottom`
    at boundary `last`. In unit terms that reads as "the package plus one unit
    above it", because the carrying boundaries sit at unit tops — but in boundary
    terms it is symmetric, one anchor either side of the run.

    The consequence is that an interval is stretched one boundary wider on each
    side than the boundaries it actually dates, so no boundary lands exactly on
    its own interval's limit. That is mechanical rather than geological, and it is
    reproduced here on purpose.
    """
    k, m = package.first, package.last

    if is_first:
        # No boundary above `b[0]` to anchor against. The importer pinned
        # `t1_prop = 1` at `b[0]` itself and padded the lower anchor by the first
        # unit's thickness. This reads as an off-by-one in the original code, but
        # it is consistent across the corpus, so keep it.
        top = coords[0]
        bottom = coords[m] + (coords[1] - coords[0])
    else:
        top = coords[k - 2]
        bottom = coords[m]

    if is_last:
        # No boundary below the base of the hole either. Place the virtual lower
        # anchor so that the basal boundary lands on BASAL_PROPORTION.
        bottom = top + (bottom - top) / (1 - BASAL_PROPORTION)

    return top, bottom


def eodp_surfaces(units: list[Unit]) -> list[AgeModelSurface]:
    """Build the age-model surfaces for a section, constraining only a few.

    `units` are ordered by `position_bottom` ascending and carry their
    `fo` interval on `b_age`.

    Only the surfaces this module can actually justify get a `relative_age`: the
    first and last carrying boundary of each package, plus the base of the hole.
    Everything between them is modeled by applying the interpolation age mdoels.
    """
    if not units:
        return []

    coords = cumulative_thickness(units)
    packages = group_packages(units)
    n = len(units)

    constraints: dict[int, RelativeAge] = {}
    for index, package in enumerate(packages):
        is_first = index == 0
        is_last = index == len(packages) - 1
        top, bottom = _package_anchors(
            package, coords, is_first=is_first, is_last=is_last
        )
        span = bottom - top
        if span <= 0:
            log.warning(
                "Section %s: package %s has no thickness; skipping constraints",
                units[0].section_id,
                package.interval.name,
            )
            continue

        # Boundaries carrying this package's interval sit at the top of each of
        # its units. The last package also carries the base of the hole.
        carried = list(range(package.first - 1, package.last))
        if is_last:
            carried.append(package.last)

        # Constrain only the endpoints — the rest are collinear with them.
        for i in {carried[0], carried[-1]}:
            constraints[i] = RelativeAge(package.interval, (bottom - coords[i]) / span)

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
    """
    rows = db.run_query(
        """
        SELECT id, section_id, col_id, position_top, position_bottom, fo, lo
        FROM macrostrat.units
        WHERE section_id = :section_id
        ORDER BY position_bottom
        """,
        dict(section_id=section_id),
    ).fetchall()

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
