"""Choose a rendering color for each legend entry of one map.

`maps.legend.color` starts as the color of the tightest geologic interval that
brackets the unit's modeled age. Many units share an interval, so each is
nudged to a variant of that color to keep same-age neighbours distinguishable. Which variant used to be a coin
toss, so two maps of the same ground -- SGMC and NGS's corrected copy of it --
disagreed on every unit whose name differed.

The variant is now chosen from where the unit is and how big it is: its
polygons' bounding-box center snapped to a coarse grid, and the integer log2 of
its area. Both survive the small geometry corrections a re-mapping applies
(measured 2026-09-17: 98.7% of true NGS/SGMC correspondences keep the same
cell at 0.5 degrees), and together they still separate most same-age
neighbours. See the *Map coloring stability* feature note in the workbench.
"""

import hashlib
import math
from dataclasses import dataclass

import spectra

__all__ = ["CELL_SIZE", "LegendRow", "assign_colors", "color_key", "color_variants"]

# Grid cell, in degrees, that a legend's bounding-box center is snapped to.
CELL_SIZE = 0.5

# Lightness and chroma moves around the base color, in spectra's Lab units.
# Today's variants reached the same +-9 lightness in three steps; these steps
# are gentler, so adjacent variants read as the same unit.
_LIGHTNESS_STEPS = (0, 3, -3, 6, -6, 9, -9)
_SATURATION_STEPS = (0, 12, -12)


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
    # Areas below 1 km^2 collapse into one class rather than spreading over
    # negative powers, where small absolute changes would flip the class.
    size_class = math.floor(math.log2(max(area_km, 1.0)))
    return (math.floor(cx / cell), math.floor(cy / cell), size_class)


def variant_index(key: tuple[int, int, int], n: int) -> int:
    """Deterministic index in `range(n)`, independent of Python's hash seed."""
    digest = hashlib.md5(":".join(str(k) for k in key).encode()).hexdigest()
    return int(digest[:8], 16) % n


def color_variants(base: str) -> list[str]:
    """Variants of `base`, index 0 being `base` itself unaltered."""
    color = spectra.html(base)
    variants = []
    for ds in _SATURATION_STEPS:
        for dl in _LIGHTNESS_STEPS:
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
    variants[0] = base
    return variants


def assign_colors(rows: list[LegendRow]) -> dict[int, str]:
    """Return `{legend_id: color}` for the rows whose color should change.

    Every row with a readable base color and some polygons takes the variant
    its place-and-size key selects, so a unit's color is a function of its
    age, place and size alone. Groups used to be exempt when they had one
    member; that made the same unit differ between a map where its age was
    unique and one where it was not, for no visible benefit.
    """
    changes: dict[int, str] = {}
    variants_by_base: dict[str, list[str]] = {}
    for row in rows:
        if not row.color or row.cx is None or row.cy is None or row.area_km is None:
            continue
        base = row.color
        if base not in variants_by_base:
            try:
                variants_by_base[base] = color_variants(base)
            except ValueError:
                # Not a color spectra can read; leave it alone.
                variants_by_base[base] = [base]
        variants = variants_by_base[base]
        idx = variant_index(color_key(row.cx, row.cy, row.area_km), len(variants))
        if variants[idx] != base:
            changes[row.legend_id] = variants[idx]
    return changes
