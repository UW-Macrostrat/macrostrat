"""`normalize review-points`: fill a staged points table's blank columns from
the points' own metadata, and clear what `maps.points` would refuse.

A value a point already has is kept; a blank one is filled:

- `strike` from its azimuth (`STRIKES`), `dip` from its inclination (`DIPS`).
  A placeholder (-1, -9, -999) or a value outside `maps.points`' check
  constraints is not written, and a point's own strike, dip or dip_dir out of
  range is cleared, or the insert fails (`RANGES`);
- `point_type` from its type (`POINT_TYPES`), "not assigned" counting as blank;
- `certainty` from its identity confidence (`CONFIDENCE`);
- `descrip` from its most descriptive text (`DESCRIPTIONS`), with a type or
  note that says more added to it;
- `comments` from its description where that says more than its type, and a
  dated sample's age ("K-Ar biotite 20.4 ± 0.4 Ma").

`point_type` and `certainty` are cut to `maps.points`' 100 characters
(`fit`): parenthetical asides first, then whole words. The full text is in
descrip.

Nothing is omitted. Which layers are geology is `normalize review-layers`, and
which points say nothing at all is reported by `macrostrat maps process preflight`.

Every value in a point's metadata that says something and is carried into none
of these columns is reported in the terminal, as is each measurement not
written; `--out` also writes them to a CSV.
"""

import re
from collections import Counter
from typing import Callable, Optional

from psycopg.sql import SQL, Identifier

from ..utils.feature_text import first, pertinent, words

#: Where a point's strike or trend is, and its dip or plunge.
STRIKES = ["azimuth", "azimuthn", "strike/trend", "azimuth_1"]
DIPS = ["inclination", "inclinationn", "dip/plunge", "inclination_1"]

#: What `maps.points` accepts (its check constraints strike_positive,
#: strike_lt_360, dip_positive, dip_lt_90, direction_positive,
#: direction_lt_360): a value outside is cleared, or the insert fails.
RANGES = {"strike": (0, 360), "dip": (0, 90), "dip_dir": (0, 360)}

#: A new value that clears the point's own: written as null.
CLEAR = ""

#: `maps.points.point_type` and `certainty` are varchar(100).
MAX_TEXT = 100

#: Where its type is, for `point_type`.
POINT_TYPES = ["type", "pttype", "structure type", "descrip"]

#: Where its description is, most descriptive first.
DESCRIPTIONS = [
    "descrip",
    "notes",
    "comments",
    "structure type",
    "pttype",
    "type",
    "point_type",
]

#: Where its identity confidence is, for a blank `certainty`.
CONFIDENCE = ["identityconfidence", "identity confidence"]

#: The columns this writes.
TARGETS = ["point_type", "strike", "dip", "dip_dir", "certainty", "descrip", "comments"]

#: Columns that say nothing a point's own columns do not: ids, symbols,
#: editing records, coordinates, its map unit (the polygon under it), the
#: symbol's rotation and scale, the other confidences, and the geochron fields
#: read into `comments`. Never reported.
ACCOUNTED = {
    "_pkid", "source_id", "source_layer", "orig_id", "omit", "objectid",
    "globalid", "ruleid", "symbol", "fgdcsymbol", "override", "datasourceid",
    "data source", "created_user", "created_date", "last_edited_user",
    "last_edited_date", "label", "locationconfidencemeters",
    "locationmethod", "identitytext", "existenceconfidence",
    "mapunit", "observedmapunit", "gpsx", "gpsy", "mapx", "mapy", "utme", "utmn",
    "utmzone", "zone", "datum", "nad27_x", "nad27_y", "pdop", "elevation in meters",
    "stationid", "fieldid", "fieldsampleid", "alternatesampleid", "sampleno",
    "mapno", "orientationsourceid", "locationsourceid", "analysissourceid",
    "symbolrotation", "symbol rotation", "rotation", "plotatscale",
    "plotatscalen", "pas", "lcm", "orientationconfidencedegrees",
    "orientationconfidencedegreesn", "locationconfidencemetersn",
    "age", "numericage", "numericagen", "ageunits", "agepluserror",
    "ageminuserror", "agepluserrorn", "ageminuserrorn", "materialanalyzed",
    "observer", "timedate", "local date", "geologist", "projectarea",
    "islocked", "displayname", *TARGETS, *STRIKES, *DIPS, *CONFIDENCE,
}  # fmt: skip


def accounted(column: str) -> bool:
    """A column that is never reported: `ACCOUNTED`, a feature id
    (orientationpoints_id), ArcGIS's editing columns (syscreatedby), and a copy
    of any of them with a "_1" suffix (displayname_1)."""
    base = re.sub(r"_\d+$", "", column)
    return (
        base in ACCOUNTED
        or column in ACCOUNTED
        or base.endswith("_id")
        or base.startswith("sys")
    )


def fit(text: Optional[str], limit: int = MAX_TEXT) -> Optional[str]:
    """`text` cut to `limit` characters: parenthetical asides dropped first,
    then whole words."""
    if text is None or len(text) <= limit:
        return text
    text = re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)", " ", text)).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0]


def _measure(point: dict, column: str, sources: list[str], issues: list):
    """A point's strike or dip: its own if in range, else the first of
    `sources` that is; placeholders and out-of-range values are reported.
    `CLEAR` where the point's own is out of range and none of `sources`
    replaces it."""
    low, high = RANGES[column]
    for source in [column, *sources]:
        raw = point.get(source)
        if raw in (None, "", " "):
            continue
        try:
            value = float(str(raw).strip())
        except ValueError:
            issues.append((source, f"{column} not a number", str(raw), ""))
            continue
        if low <= value <= high:
            return str(round(value))
        issues.append((source, f"{column} placeholder or out of range", str(raw), ""))
    return CLEAR if point.get(column) not in (None, "", " ") else None


def _geochron(point: dict) -> Optional[str]:
    """A dated sample's age as one phrase: "K-Ar biotite 20.4 ± 0.4 Ma"."""
    age = point.get("numericage") or point.get("age")
    if age in (None, "", " "):
        return None
    error = point.get("agepluserror")
    parts = [
        pertinent(point.get("point_type")) or pertinent(point.get("type")),
        pertinent(point.get("materialanalyzed")),
        f"{age}" + (f" ± {error}" if error not in (None, "", " ") else ""),
        pertinent(point.get("ageunits")) or "",
    ]
    return " ".join(p for p in parts if p).strip()


def review_point(point: dict) -> tuple[dict, list[tuple[str, str, str, str]]]:
    """(the point's new {column: value}, [(column, issue, value, new value)])."""
    issues = []
    point_type = pertinent(point.get("point_type")) or first(point, POINT_TYPES)
    strike = _measure(point, "strike", STRIKES, issues)
    dip = _measure(point, "dip", DIPS, issues)
    certainty = pertinent(point.get("certainty")) or first(point, CONFIDENCE)
    descrip = first(point, DESCRIPTIONS)
    # A type or note that says more ("lineation, stretch/shape (mylonitic)"
    # where descrip is "lineation") is added to it. Comments are kept apart.
    for column in DESCRIPTIONS:
        extra = pertinent(point.get(column)) if column != "comments" else None
        if not extra or words(extra) <= words(descrip) | words(point_type):
            continue
        descrip = extra if words(descrip) <= words(extra) else f"{descrip}; {extra}"

    # Comments a point has are kept, whatever they say.
    comments = re.sub(r"\s+", " ", str(point.get("comments") or "")).strip() or None
    if comments is None and descrip and not words(descrip) <= words(point_type):
        comments = descrip
    number = str(point.get("numericage") or point.get("age") or "")
    if (
        (age := _geochron(point))
        and not words(age) <= words(comments)
        and number not in (comments or "")
    ):
        comments = f"{comments}; {age}" if comments else age

    new = dict(
        point_type=fit(point_type),
        strike=strike,
        dip=dip,
        certainty=fit(certainty),
        descrip=descrip,
        comments=comments,
    )
    # dip_dir is otherwise left as it is, but one out of range is cleared.
    if point.get("dip_dir") not in (None, "", " "):
        try:
            ok = 0 <= float(point["dip_dir"]) <= 360
        except ValueError:
            ok = False
        if not ok:
            issues.append(
                ("dip_dir", "dip_dir out of range: cleared", str(point["dip_dir"]), "")
            )
            new["dip_dir"] = CLEAR

    carried = words(" ".join(v for v in new.values() if v))
    for column, raw in point.items():
        if accounted(column):
            continue
        if (value := pertinent(raw)) is None or words(value) <= carried:
            continue
        # Not in point_type, descrip, comments or certainty.
        issues.append((column, "not mapped", value, ""))
    return new, issues


def _old(point: dict, column: str) -> str:
    raw = point.get(column)  # a strike or dip of 0 is a value
    old = "" if raw is None else re.sub(r"\s+", " ", str(raw)).strip()
    if column in RANGES and old:
        try:
            old = str(round(float(old)))
        except ValueError:
            pass
    return old


def review_points_table(
    db, slug: str, table: str, dry_run: bool, log: Counter, examples: dict
) -> dict[str, int]:
    """Review one map's `sources.<table>` points; see `review_table`."""
    return review_table(db, slug, table, review_point, TARGETS, dry_run, log, examples)


def review_table(
    db,
    slug: str,
    table: str,
    review: Callable[[dict], tuple[dict, list]],
    targets: list[str],
    dry_run: bool,
    log: Counter,
    examples: dict,
    prepare: Optional[Callable[[list[dict]], None]] = None,
) -> dict[str, int]:
    """Review each feature of `sources.<table>` not omitted with `review`
    (feature -> ({column: new value}, [(column, issue, value, new value)])),
    write the new values that differ from the feature's own, and tally what is
    reported into `log`, keyed (slug, source_layer, column, issue, value, new
    value). `prepare` sees every feature first and may change them. Returns how
    many features each column is written for."""
    types = dict(
        db.run_query(
            """
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'sources' AND table_name = :table
            """,
            dict(table=table),
        ).all()
    )
    if not types:
        return {}
    if "_pkid" not in types:
        raise ValueError(f"sources.{table} has no _pkid; it has not been prepared")
    relation = Identifier("sources", table)
    features = [
        f
        for f in db.run_query(
            "SELECT to_jsonb(f) - 'geom' - 'geometry' FROM {table} f",
            dict(table=relation),
        ).scalars()
        if f.get("omit") is not True
    ]
    originals = {f["_pkid"]: dict(f) for f in features}
    if prepare is not None:
        prepare(features)

    writes = {column: ([], []) for column in targets}
    for feature in features:
        layer = str(feature.get("source_layer"))
        new, issues = review(feature)
        for column, issue, value, new_value in issues:
            key = (slug, layer, column, issue, value, new_value)
            log[key] += 1
            examples.setdefault(key, feature["_pkid"])
        # What `prepare` set is written too.
        own = originals[feature["_pkid"]]
        for column in targets:
            if column in new:
                value = new[column]
            elif feature.get(column) != own.get(column):
                value = feature.get(column)
            else:
                continue
            if value is not None and value != _old(own, column):
                writes[column][0].append(feature["_pkid"])
                writes[column][1].append(None if value == CLEAR else str(value))

    counts = {}
    for column, (ids, values) in writes.items():
        if not ids:
            continue
        counts[column] = len(ids)
        if column not in types:
            key = (slug, "", column, "column missing: not written", "", "")
            log[key] += len(ids)
            continue
        if dry_run:
            continue
        db.run_query(
            """
            UPDATE {table} t SET {column} = CAST(v.value AS {type})
            FROM unnest(CAST(:ids AS bigint[]), CAST(:vals AS text[]))
              AS v(_pkid, value)
            WHERE t._pkid = v._pkid
            """,
            dict(
                table=relation,
                column=Identifier(column),
                type=SQL(types[column]),
                ids=ids,
                vals=values,
            ),
        )
    if not dry_run:
        db.session.commit()
    return counts
