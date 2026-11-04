"""Choose a rendering color for each legend entry of one map.

`maps.legend.color` starts as the color of the tightest geologic interval that
brackets the unit's modeled age. Where several units of one map share that
color and age, all but the largest are nudged to variants of it so same-age
neighbours stay distinguishable; a unit alone in its age keeps the interval
color. Which variant used to be a coin toss, so two maps of the same ground --
SGMC and NGS's corrected copy of it -- disagreed on every unit whose name
differed.

The variant is now chosen from where the unit is and how big it is: its
polygons' bounding-box center snapped to a coarse grid, and the integer log2 of
its area. Both survive the small geometry corrections a re-mapping applies
(measured 2026-09-17: 98.7% of true NGS/SGMC correspondences keep the same
cell at 0.5 degrees), and together they still separate most same-age
neighbours. See the *Map coloring stability* feature note in the workbench.
"""

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass

import spectra

__all__ = ["CELL_SIZE", "LegendRow", "assign_colors", "color_key", "color_variants"]

# Grid cell, in degrees, that a legend's bounding-box center is snapped to.
CELL_SIZE = 0.5

# Lightness and chroma moves from the base color, in spectra's Lab units: the
# variants used before 2026-09, one move each.
_MOVES = (
    (3, 0),
    (-3, 0),
    (6, 0),
    (-6, 0),
    (9, 0),
    (-9, 0),
    (0, 10),
    (0, -10),
    (0, -20),
    (0, 20),
    (0, 30),
)

# Below this chroma a color is gray and its hue is noise; saturating would invent one.
_ACHROMATIC = 1.0


@dataclass(frozen=True)
class LegendRow:
    legend_id: int
    color: str | None
    best_age_top: float | None
    best_age_bottom: float | None
    # Center of the bounding box of the legend's polygons, in degrees, and
    # their total area in km^2. Absent when the legend has no polygons.
    cx: float | None
    cy: float | None
    area_km: float | None


def color_key(
    cx: float, cy: float, area_km: float, cell: float = CELL_SIZE
) -> tuple[int, int, int]:
    """The stable identity a variant is chosen from: grid cell and size class."""
    # `area_km` arrives from a parallel `sum(ST_Area(...))`, and a parallel
    # aggregate adds its workers' partial sums in whatever order they finish, so
    # the value differs in its last bits between runs on identical input. That is
    # invisible until an area lands near a power of two, where `floor(log2(...))`
    # flips and the legend entry changes colour for no reason. Rounding to six
    # significant figures is far inside any real difference in area and far
    # outside the noise.
    area_km = float(f"{max(area_km, 1.0):.6g}")
    # Areas below 1 km^2 collapse into one class rather than spreading over
    # negative powers, where small absolute changes would flip the class.
    size_class = math.floor(math.log2(area_km))
    return (math.floor(cx / cell), math.floor(cy / cell), size_class)


def variant_index(key: tuple[int, int, int], n: int) -> int:
    """Deterministic index in `range(n)`, independent of Python's hash seed."""
    digest = hashlib.md5(":".join(str(k) for k in key).encode()).hexdigest()
    return int(digest[:8], 16) % n


def color_variants(base: str) -> list[str]:
    """Variants of `base`, index 0 being `base` itself unaltered."""
    color = spectra.html(base)
    chroma = color.to("lch").values[1]
    variants = [base]
    for dl, ds in _MOVES:
        # spectra lets chroma go negative, which turns the hue around; keep at least half.
        ds = max(ds, -chroma / 2)
        if chroma < _ACHROMATIC:
            ds = 0
        c = color
        if dl > 0:
            c = c.brighten(amount=dl)
        elif dl < 0:
            c = c.darken(amount=-dl)
        if ds > 0:
            c = c.saturate(amount=ds)
        elif ds < 0:
            c = c.desaturate(amount=-ds)
        variants.append(c.hexcode)
    return variants


def assign_colors(rows: list[LegendRow]) -> dict[int, str]:
    """Return `{legend_id: color}` for the rows whose color should change.

    Rows with polygons are grouped by base color and age. In a group of two
    or more, the largest keeps the base and the others take the variant their
    place-and-size key selects; a row alone in its group is left as it is.
    """
    groups: dict[tuple, list[LegendRow]] = defaultdict(list)
    for row in rows:
        if not row.color or row.cx is None or row.cy is None or row.area_km is None:
            continue
        groups[(row.color, row.best_age_top, row.best_age_bottom)].append(row)

    changes: dict[int, str] = {}
    for (base, _, _), members in groups.items():
        if len(members) < 2:
            continue
        try:
            variants = color_variants(base)
        except ValueError:
            # Not a color spectra can read; leave it alone.
            continue
        keeper = max(members, key=lambda r: (r.area_km, r.legend_id))
        for row in members:
            if row is keeper:
                continue
            key = color_key(row.cx, row.cy, row.area_km)
            color = variants[1 + variant_index(key, len(variants) - 1)]
            if color != base:
                changes[row.legend_id] = color
    return changes
