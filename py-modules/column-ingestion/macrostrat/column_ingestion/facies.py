"""The optional `facies` sheet: named lithologies and environments that units refer to.

A unit gives facies by `facies_id` in its `facies` field. Field by field, a unit's own
lithology and environment win; its facies fill only what the unit leaves blank.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from . import notices
from .environs import Environ
from .lithologies import LithAbundance, Lithology

_PROPORTION = re.compile(r"^(.*?)\s*\(([^)]*)\)\s*$")


@dataclass
class Facies:
    id: str
    name: str | None = None
    description: str | None = None
    lithology: set[Lithology] = field(default_factory=set)
    environment: set[Environ] = field(default_factory=set)


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def facies_from_df(df, vocab) -> dict[str, Facies]:
    """The facies sheet, keyed by `facies_id`, resolved against `vocab`."""
    facies: dict[str, Facies] = {}
    for number, row in enumerate(df.iter_rows(named=True), start=2):
        with notices.notice_context(sheet="facies", row=number):
            facies_id = _text(row.get("facies_id"))
            if facies_id is None:
                if any(_text(v) for v in row.values()):
                    notices.warning(
                        "facies-missing-id",
                        "No `facies_id`, so no unit can refer to it; the row was left "
                        "out",
                        column="facies_id",
                    )
                continue
            if facies_id in facies:
                notices.warning(
                    "facies-duplicate-id",
                    f"`facies_id` {facies_id!r} is used twice; this row was left out",
                    column="facies_id",
                )
                continue
            with notices.notice_context(column="lithology"):
                liths = vocab.liths(_text(row.get("lithology")), LithAbundance.DOMINANT)
            with notices.notice_context(column="environment"):
                environs = vocab.environs(_text(row.get("environment")))
            facies[facies_id] = Facies(
                id=facies_id,
                name=_text(row.get("facies")),
                description=_text(row.get("description")),
                lithology=liths,
                environment=environs,
            )
    return facies


def parse_facies_refs(text) -> list[tuple[str, float | None]]:
    """A unit's `facies` cell: ids separated by `;` or `,`, each with an optional
    `(proportion)` as a fraction or a percentage."""
    text = _text(text)
    if text is None:
        return []
    refs = []
    for part in re.split(r"[;,]", text):
        part = part.strip()
        if not part:
            continue
        proportion = None
        match = _PROPORTION.match(part)
        if match:
            part, value = match.group(1).strip(), match.group(2).strip()
            proportion = _fraction(value)
        refs.append((part, proportion))
    return refs


def _fraction(value: str) -> float | None:
    try:
        if value.endswith("%"):
            return float(value[:-1]) / 100
        return float(value)
    except ValueError:
        # Qualitative proportions (`major`, `minor`) do not scale lithologies
        return None


def facies_for_unit(
    text, known: dict[str, Facies]
) -> list[tuple[Facies, float | None]]:
    """The facies a unit names, warning about ids the facies sheet does not define."""
    found = []
    for facies_id, proportion in parse_facies_refs(text):
        facies = known.get(facies_id)
        if facies is None:
            notices.warning(
                "unknown-facies",
                f"No facies {facies_id!r} on the facies sheet",
                column="facies",
            )
            continue
        found.append((facies, proportion))
    return found


def facies_lithology(found: list[tuple[Facies, float | None]]) -> set[Lithology]:
    """The facies' lithologies, scaled by each facies' proportion where both are given."""
    liths: set[Lithology] = set()
    for facies, proportion in found:
        for lith in facies.lithology:
            if proportion is not None and lith.prop is not None:
                lith = replace(lith, prop=lith.prop * proportion)
            liths.add(lith)
    return liths


def facies_environment(found: list[tuple[Facies, float | None]]) -> set[Environ]:
    environs: set[Environ] = set()
    for facies, _ in found:
        environs |= facies.environment
    return environs
