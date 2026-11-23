"""`normalize review-layers`: every source layer in a map's staged tables, with
what its features say, and which look like no part of the geologic map.

A layer is flagged for omission when it is one of GeMS's (or ArcGIS's)
drafting, index or field-data layers (`NOT_GEOLOGY`), or when none of its
features says what it is (`preflight.DETAILS`). The command shows each layer's
columns and example values so the flag can be checked, tags each map with more
than one layer of a kind `extra-poly-layers` / `extra-line-layers` /
`extra-point-layers`, and asks before omitting anything.
"""

import re
from dataclasses import dataclass, field

from .preflight import layer_counts, layer_details

#: Layers that are not the geologic map, whatever their features say.
NOT_GEOLOGY = {
    # Data source footprints, the correlation chart's boxes, cross sections,
    # overlays drawn on top of the map units.
    "polygons": re.compile(
        r"datasourcepolys|cmu|x_?sec|cross.?section|csa|overlaypolys|anno", re.I
    ),
    # Drafting: CartographicLines (leaders, quad boundaries, section lines),
    # the correlation chart's CMULines, ArcGIS validation errors, annotation.
    "lines": re.compile(
        r"cartographiclines|cmulines|validation|errors|leader|anno|x_?sec|"
        r"cross.?section|csa_line",
        re.I,
    ),
    # Field stations and their waypoints, sample sites, label and photo points.
    "points": re.compile(
        r"station|sample|genericpoints|mapunitpolyspoints|analyticaldata|anno",
        re.I,
    ),
}


@dataclass
class Layer:
    kind: str
    name: str
    features: int
    described: int
    omitted: int
    #: Why it should be omitted; empty when it looks like geology.
    flag: str = ""
    #: (column, features with a value, "n distinct: example | example").
    columns: list[tuple[str, int, str]] = field(default_factory=list)


def review_map_layers(db, slug: str, kinds: list[str]) -> list[Layer]:
    """Every source layer of a map's staged tables, flagged and described."""
    layers = []
    for kind in kinds:
        counts = layer_counts(db, slug, kind)
        if not counts:
            continue
        details = {}
        for finding in layer_details(db, slug, kind):
            details.setdefault(finding.source_layer, []).append(
                (finding.check.removeprefix("column "), finding.count, finding.detail)
            )
        for name, (n, described, omitted) in counts.items():
            layer = Layer(
                kind, name, n, described, omitted, columns=details.get(name, [])
            )
            if n == 0:
                pass  # already omitted
            elif NOT_GEOLOGY[kind].search(name):
                layer.flag = "not the geologic map (drafting, index or field data)"
            elif described == 0:
                layer.flag = "no feature says what it is"
            layers.append(layer)
    return layers


def ilike_literal(text: str) -> str:
    """`text` as an ILIKE pattern that matches only itself."""
    return re.sub(r"([\\%_])", r"\\\1", text)
