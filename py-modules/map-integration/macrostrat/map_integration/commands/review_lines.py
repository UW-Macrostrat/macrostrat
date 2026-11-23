"""`normalize review-lines`: fill a staged lines table's blank columns from the
lines' own metadata. The lines' counterpart of `review-points`.

A value a line already has is kept; a blank one is filled:

- `type` from its type columns (`TYPES`), else from the lines drawn with the
  same ArcGIS representation rule in its layer (`gems_utils.infer_line_types`:
  at least 5 typed lines, 90% agreeing);
- `certainty` from its identity confidence (`CONFIDENCE`);
- `name` from the feature it is, where its metadata names one
  ("Buckskin-Rawhide detachment fault"), else its label (`LABELS`);
- `descrip` from its most descriptive text (`DESCRIPTIONS`), with any throw
  direction Macrostrat has no `direction` for added ("ball on downthrown
  side", "down to the southwest"), and "(concealed)" where `isconcealed` says so;
- `direction` from the sense of slip or fold Macrostrat records (`DIRECTIONS`).

`type`, `name` and `direction` are cut to their `maps.lines` lengths (100, 255,
40). Nothing is omitted: which layers are geology is `normalize review-layers`,
and which lines say nothing at all is reported by `macrostrat maps process
preflight`.

Every value in a line's metadata that says something and is carried into none
of these columns is reported, with conflicting directions.
"""

import re
from typing import Optional

from ..utils.feature_text import first, pertinent, words
from .review_points import fit

#: Where a line's type is, for a blank `type`.
TYPES = ["type", "line type", "ltype"]

#: Where its description is, most descriptive first.
DESCRIPTIONS = [
    "descrip",
    "text description",
    "display name",
    "line type",
    "ltype",
    "notes",
    "name",
    "label",
    "line label",
    "type",
]

#: Where its label is, for `name` when no feature is named.
LABELS = ["name", "label", "line label", "display name"]

#: Where its identity confidence is, for a blank `certainty`.
CONFIDENCE = ["identityconfidence", "identity confidence"]

#: The columns this writes, and their `maps.lines` lengths.
TARGETS = ["type", "name", "descrip", "direction", "certainty"]
LENGTHS = {"type": 100, "name": 255, "direction": 40}

#: Columns that hold no description of the line: ids, symbols, provenance,
#: editing records, measurements, the other confidences. Never reported.
SYSTEM = {
    "_pkid", "source_id", "source_layer", "orig_id", "omit", "objectid",
    "globalid", "ruleid", "symbol", "symbol set", "fgdcsymbol", "override",
    "shape_length", "shape_area", "datasourceid", "data source",
    "newdatasourceid", "created_user", "created_date", "last_edited_user",
    "last_edited_date", "created date", "created by", "updated date",
    "updated by", "edit count", "tracking", "status", "validation status",
    "owning repository", "sysguid", "ncgmpid", "cartoobjid", "classifier",
    "classifier type", "sub type", "map horizon", "locatability",
    "depiction scale", "position uncertainty", "locationconfidencemeters",
    "location confidence (in meters)", "locationmethod", "identifier", "long",
    "isconcealed", "layer", "entity", "color", "linetype", "elevation",
    "linewt", "identitytext", "existenceconfidence", "existence confidence",
    *CONFIDENCE,
}  # fmt: skip

#: Macrostrat's line directions (`maps.lines.direction`), and the words for them.
DIRECTIONS = [
    ("right-lateral", re.compile(r"right[\s-]*lateral|dextral", re.I)),
    ("left-lateral", re.compile(r"left[\s-]*lateral|sinistral", re.I)),
    ("overturned", re.compile(r"overturned", re.I)),
    ("plunging", re.compile(r"plung", re.I)),
]

#: A direction Macrostrat has no value for: which side is down, or the side
#: the symbol's ball, teeth or hachures are on. It goes in the description.
OTHER_DIRECTION = re.compile(
    r"downthrown|upthrown|down[\s-]+to|hanging\s*wall|teeth|ball\b|"
    r"\bhach|\bhatch|showing dip|dip direction|\bu/d\b",
    re.I,
)

#: A named feature: proper-noun words before what it is.
FEATURE = re.compile(
    r"((?:[A-Z][\w'.]*(?:[\s-]+|$))+?)"
    r"(?i:(?:detachment\s+)?(?:fault(?:\s+zone|\s+system)?|detachment|"
    r"shear\s+zone|anticline|syncline|monocline|lineament|dike|vein)s?)\b"
)

#: Capitalised words that do not make a name: "High-angle fault", "Accurately
#: located fault".
GENERIC = set(
    """high low angle normal reverse thrust strike slip oblique accurate
    accurately approximate approximately concealed inferred located queried
    certain uncertain gravity slide contact depositional lithogenetic boundary
    detachment fault fold mafic felsic quartz overturned plunging right left
    lateral subsidiary major minor buried scarp internal unit map line
    observed showing dip type unspecified fault certain the""".split()
)


def system(column: str) -> bool:
    """A column that does not describe the line: `SYSTEM`, or a feature id
    (contactsandfaults_id)."""
    return column in SYSTEM or column.endswith("_id") or column.startswith("sys")


def named_feature(texts: list[str]) -> Optional[str]:
    """The named feature in the first of `texts` naming one."""
    for text in texts:
        for match in FEATURE.finditer(text):
            found = re.findall(r"[A-Za-z]+", match.group(1))
            if found and not all(w.lower() in GENERIC for w in found):
                return re.sub(r"\s+", " ", match.group(0)).strip()
    return None


def review_line(line: dict) -> tuple[dict, list[tuple[str, str, str, str]]]:
    """(the line's new {column: value}, [(column, issue, value, new value)])."""
    issues = []
    texts = [v for c, raw in line.items() if not system(c) and (v := pertinent(raw))]

    line_type = pertinent(line.get("type")) or first(line, TYPES)
    certainty = pertinent(line.get("certainty")) or first(line, CONFIDENCE)

    descrip = first(line, DESCRIPTIONS)
    for throw in dict.fromkeys(t for t in texts if OTHER_DIRECTION.search(t)):
        if descrip is None or words(descrip) <= words(throw):
            descrip = throw
        elif not words(throw) <= words(descrip):
            descrip = f"{descrip}; {throw}"
    concealed = str(line.get("isconcealed") or "").strip().lower()
    if (
        descrip
        and concealed in ("y", "yes", "true", "1")
        and "conceal" not in descrip.lower()
    ):
        descrip += " (concealed)"

    name = named_feature(texts) or first(line, LABELS)

    found = {value for value, pattern in DIRECTIONS for t in texts if pattern.search(t)}
    if len(found) > 1:
        issues.append(
            ("direction", "conflicting directions", "; ".join(sorted(found)), "")
        )
    direction = (found.pop() if len(found) == 1 else None) or pertinent(
        line.get("direction")
    )

    new = dict(
        type=fit(line_type, LENGTHS["type"]),
        certainty=certainty,
        name=fit(name, LENGTHS["name"]),
        descrip=descrip,
        direction=fit(direction, LENGTHS["direction"]),
    )
    carried = words(" ".join(v for v in new.values() if v))
    for column, raw in line.items():
        if system(column) or (value := pertinent(raw)) is None:
            continue
        if words(value) <= carried:
            continue
        if OTHER_DIRECTION.search(value):
            issues.append((column, "direction with no Macrostrat value", value, ""))
        else:
            issues.append((column, "not mapped", value, ""))
    return new, issues


def type_from_rules(lines: list[dict]) -> None:
    """Give the lines with no type the type of the lines drawn with the same
    representation rule in their layer (`gems_utils.infer_line_types`)."""
    import pandas as pd

    from ..utils.gems_utils import infer_line_types

    if not lines or "ruleid" not in lines[0]:
        return
    df = pd.DataFrame(
        {
            "source_layer": [line.get("source_layer") for line in lines],
            "ruleid": [line.get("ruleid") for line in lines],
            "type": [line.get("type") for line in lines],
            "descrip": [line.get("descrip") for line in lines],
        }
    )
    df, typed = infer_line_types(df)
    if not typed:
        return
    for line, line_type, descrip in zip(lines, df["type"], df["descrip"]):
        if line_type is not None and not pd.isna(line_type):
            line["type"] = line_type
        if descrip is not None and not pd.isna(descrip):
            line["descrip"] = descrip


def review_lines_table(db, slug: str, table: str, dry_run: bool, log, examples):
    """Review one map's `sources.<table>` lines; see `review_points.review_table`."""
    from .review_points import review_table

    return review_table(
        db,
        slug,
        table,
        review_line,
        TARGETS,
        dry_run,
        log,
        examples,
        prepare=type_from_rules,
    )
