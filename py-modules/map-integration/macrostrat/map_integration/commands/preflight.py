"""`macrostrat maps process preflight`: what `macrostrat maps process insert` would refuse in
a map's staged tables, and which of its layers say nothing about their
features. Reads only.

**Insert blockers.** Each fails `copy_to_maps` (or its SQL) partway, leaving the
map half inserted:

- no scale on `maps.sources`, no polygons table, or no polygons left to copy;
- a column the copy reads (`COPIED`) missing from a staged table, or of a type
  the maps column cannot take (text into `maps.points.strike`, an integer);
- geometry `maps.polygons` / `maps.lines` / `maps.points` refuses: invalid, or
  not (multi)polygons and (multi)lines (`fix-geometries` repairs these);
- strike, dip or dip_dir outside `maps.points`' check constraints
  (`review-points` clears them);
- text longer than its `maps` column (`point_type` and `certainty` 100,
  `lines.type` 100, `lines.name` 255, `lines.direction` 40, `polygons.age` 255);
- `lith`, `t_interval` or `b_interval` null on every polygon, which the insert
  refuses without `--allow-unattributed`.

Staged rows whose `source_id` is not the map's are reported too: the copy
skips them without saying so.

**Layers with no details.** A polygons, lines or points table none of whose
features says what it is (`DETAILS`: no name, description, type, lithology...)
is reported with every column it does have, per source layer: how many
features have a value and examples of them. That is what to work from in
data-integration to decide the legend merge or column mapping the map needs.
"""

from dataclasses import dataclass
from typing import Optional

from psycopg.sql import SQL, Identifier

from macrostrat.map_utils.slugs import staging_table

from ..utils.feature_text import BLANK, blank_sql

KINDS = ("polygons", "lines", "points")

#: The columns `copy-<kind>-to-maps.sql` reads from each staged table.
COPIED = {
    "polygons": [
        "source_id", "orig_id", "name", "strat_name", "age", "lith", "descrip",
        "comments", "t_interval", "b_interval", "geom", "omit",
    ],
    "lines": ["source_id", "orig_id", "name", "type", "direction", "descrip", "geom", "omit"],
    "points": [
        "source_id", "strike", "dip", "dip_dir", "point_type", "certainty",
        "comments", "geom", "orig_id", "omit",
    ],
}  # fmt: skip

#: The check that the maps table puts on a geometry.
GEOMETRY_CHECK = {
    "polygons": "maps.polygons_geom_is_valid(geom)",
    "lines": "maps.lines_geom_is_valid(geom)",
    "points": "ST_IsValid(geom)",
}

#: `maps.points`' check constraints.
RANGES = {"strike": (0, 360), "dip": (0, 90), "dip_dir": (0, 360)}

#: Staged column types an integer maps column can take.
NUMERIC = {"smallint", "integer", "bigint", "numeric", "real", "double precision"}

#: The polygons columns the insert refuses to find null throughout
#: (`insert.ATTEMPTED_COLUMNS`).
ATTEMPTED = ("lith", "t_interval", "b_interval")

#: What says what a feature is. A points table's strike and dip together do too.
DETAILS = {
    "polygons": [
        "name", "descrip", "comments", "strat_name", "lith", "fullname",
        "description", "generallithology", "geomaterial",
    ],
    "lines": ["name", "descrip", "type", "direction"],
    "points": ["point_type", "descrip", "comments"],
}  # fmt: skip

#: Columns left out of a layer's details: they say nothing about its features.
NOT_DETAILS = {"_pkid", "source_id", "omit", "geom", "geometry"}


@dataclass
class Finding:
    slug: str
    table: str
    check: str
    count: int = 0
    detail: str = ""
    source_layer: str = ""
    #: True when it makes the insert fail.
    blocks: bool = False


def _columns(db, table: str) -> dict[str, str]:
    return dict(
        db.run_query(
            """
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'sources' AND table_name = :table
            """,
            dict(table=table),
        ).all()
    )


def maps_limits(db) -> dict[str, dict[str, tuple[str, Optional[int]]]]:
    """{kind: {column: (data type, max length)}} for `maps.<kind>`."""
    limits = {kind: {} for kind in KINDS}
    for kind, column, data_type, length in db.run_query(
        """
        SELECT table_name, column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'maps' AND table_name = ANY(:kinds)
        """,
        dict(kinds=list(KINDS)),
    ).all():
        limits[kind][column] = (data_type, length)
    return limits


def _live(columns: dict) -> SQL:
    """The staged rows the copy takes, as far as `omit` goes."""
    return SQL("omit IS NOT TRUE") if "omit" in columns else SQL("true")


def check_table(
    db, slug: str, source_id: int, kind: str, limits: dict
) -> list[Finding]:
    """The insert blockers in one staged table."""
    table = staging_table(slug, kind)
    columns = _columns(db, table)
    if not columns:
        if kind == "polygons":
            return [Finding(slug, kind, "no polygons table", blocks=True)]
        return []
    found = []
    relation = Identifier("sources", table)
    live = _live(columns)

    missing = [c for c in COPIED[kind] if c not in columns and c != "omit"]
    if missing:
        found.append(
            Finding(
                slug, kind, "column missing", detail=", ".join(missing), blocks=True
            )
        )

    n = db.run_query(
        "SELECT count(*) FROM {table} WHERE {live}", dict(table=relation, live=live)
    ).scalar()
    if n == 0:
        if kind == "polygons":
            found.append(Finding(slug, kind, "no polygons left to copy", blocks=True))
        return found

    if "source_id" in columns:
        other = db.run_query(
            "SELECT count(*) FROM {table} WHERE {live}"
            " AND source_id IS DISTINCT FROM :source_id",
            dict(table=relation, live=live, source_id=source_id),
        ).scalar()
        if other:
            found.append(
                Finding(
                    slug,
                    kind,
                    "source_id not the map's: not copied",
                    other,
                    f"map is source {source_id}",
                )  # fmt: skip
            )

    if "geom" in columns:
        bad = db.run_query(
            "SELECT count(*) FROM {table} WHERE {live} AND NOT coalesce({check}, false)",
            dict(table=relation, live=live, check=SQL(GEOMETRY_CHECK[kind])),
        ).scalar()
        if bad:
            found.append(
                Finding(
                    slug,
                    kind,
                    "geometry maps refuses",
                    bad,
                    "invalid or the wrong type: run fix-geometries",
                    blocks=True,
                )  # fmt: skip
            )

    for column, data_type in columns.items():
        target = limits[kind].get(column)
        if target is None or column not in COPIED[kind]:
            continue
        maps_type, length = target
        if maps_type == "integer" and data_type not in NUMERIC:
            found.append(
                Finding(
                    slug,
                    kind,
                    "column type maps refuses",
                    n,
                    f"{column} is {data_type}; maps.{kind}.{column} is integer",
                    blocks=True,
                )  # fmt: skip
            )
            continue
        if column in RANGES and kind == "points" and data_type in NUMERIC:
            low, high = RANGES[column]
            out = db.run_query(
                "SELECT count(*) FROM {table} WHERE {live}"
                " AND ({column} < :low OR {column} > :high)",
                dict(
                    table=relation,
                    live=live,
                    column=Identifier(column),
                    low=low,
                    high=high,
                ),
            ).scalar()
            if out:
                found.append(
                    Finding(
                        slug,
                        kind,
                        f"{column} out of range",
                        out,
                        f"maps.points takes {low}-{high}: run review-points",
                        blocks=True,
                    )  # fmt: skip
                )
        if length is not None:
            long = db.run_query(
                "SELECT count(*), max(length(CAST({column} AS text))) FROM {table}"
                " WHERE {live} AND length(CAST({column} AS text)) > :length",
                dict(
                    table=relation, live=live, column=Identifier(column), length=length
                ),
            ).one()
            if long[0]:
                found.append(
                    Finding(
                        slug,
                        kind,
                        f"{column} too long",
                        long[0],
                        f"up to {long[1]} characters; maps.{kind}.{column} takes {length}",
                        blocks=True,
                    )  # fmt: skip
                )

    if kind == "polygons":
        empty = [
            c
            for c in ATTEMPTED
            if c not in columns
            or not db.run_query(
                "SELECT count({column}) FROM {table} WHERE {live}",
                dict(table=relation, live=live, column=Identifier(c)),
            ).scalar()
        ]
        if empty:
            found.append(
                Finding(
                    slug,
                    kind,
                    "null on every polygon",
                    n,
                    f"{', '.join(empty)}: insert needs --allow-unattributed",
                    blocks=True,
                )  # fmt: skip
            )
    return found


def _none_say(kind: str, columns: dict):
    """SQL true for a feature none of whose `DETAILS` says anything."""
    blank = [blank_sql(c) for c in DETAILS[kind] if c in columns]
    if kind == "points" and {"strike", "dip"} <= set(columns):
        blank.append(SQL("(strike IS NULL OR dip IS NULL)"))
    return SQL(" AND ").join(blank) if blank else SQL("true")


def undescribed(db, slug: str, kind: str) -> Optional[tuple[int, int]]:
    """(features, features with no details) for one staged table, or None
    without one."""
    counts = layer_counts(db, slug, kind)
    if counts is None:
        return None
    return (
        sum(n for n, _, _ in counts.values()),
        sum(n - described for n, described, _ in counts.values()),
    )


def layer_counts(db, slug: str, kind: str) -> Optional[dict[str, tuple[int, int, int]]]:
    """{source_layer: (features not omitted, of them described, omitted)} for
    one staged table, or None without one."""
    table = staging_table(slug, kind)
    columns = _columns(db, table)
    if not columns:
        return None
    layer = Identifier("source_layer") if "source_layer" in columns else SQL("''")
    omitted = SQL("omit IS TRUE") if "omit" in columns else SQL("false")
    rows = db.run_query(
        """
        SELECT coalesce(CAST({layer} AS text), ''),
               count(*) FILTER (WHERE NOT {omitted}),
               count(*) FILTER (WHERE NOT {omitted} AND NOT ({none_say})),
               count(*) FILTER (WHERE {omitted})
        FROM {table}
        GROUP BY 1
        ORDER BY 1
        """,
        dict(
            table=Identifier("sources", table),
            layer=layer,
            omitted=omitted,
            none_say=_none_say(kind, columns),
            blank_values=sorted(BLANK),
        ),
    ).all()
    return {layer: (n, described, gone) for layer, n, described, gone in rows}


def layer_details(db, slug: str, kind: str, examples: int = 3) -> list[Finding]:
    """Every column of a staged table, per source layer: how many features
    have a value, how many distinct values, and up to `examples` of them."""
    table = staging_table(slug, kind)
    columns = _columns(db, table)
    relation = Identifier("sources", table)
    layer = Identifier("source_layer") if "source_layer" in columns else SQL("''")
    found = []
    for column in columns:
        if column in NOT_DETAILS or columns[column] == "USER-DEFINED":
            continue
        rows = db.run_query(
            """
            SELECT coalesce(CAST({layer} AS text), ''),
                   count(*) FILTER (WHERE NOT {blank}),
                   count(DISTINCT CAST({column} AS text)) FILTER (WHERE NOT {blank}),
                   (array_agg(DISTINCT left(CAST({column} AS text), 80))
                      FILTER (WHERE NOT {blank}))[1\\:CAST(:examples AS integer)]
            FROM {table}
            WHERE {live}
            GROUP BY 1
            ORDER BY 1
            """,
            dict(
                table=relation,
                layer=layer,
                column=Identifier(column),
                blank=blank_sql(column),
                live=_live(columns),
                blank_values=sorted(BLANK),
                examples=examples,
            ),
        ).all()
        for source_layer, n, distinct, sample in rows:
            if not n or column == "source_layer":
                continue
            found.append(
                Finding(
                    slug,
                    kind,
                    f"column {column}",
                    n,
                    f"{distinct:,} distinct: " + " | ".join(sample or []),
                    source_layer,
                )  # fmt: skip
            )
    return found


def preflight(
    db, slug: str, source_id: int, scale: Optional[str], limits: dict, kinds=KINDS
):
    """(insert blockers and warnings, {kind: (features, undescribed)},
    details of the layers none of whose features is described)."""
    findings = []
    if scale is None:
        findings.append(Finding(slug, "", "no scale on maps.sources", blocks=True))
    counts, details = {}, []
    for kind in kinds:
        findings += check_table(db, slug, source_id, kind, limits)
        if (count := undescribed(db, slug, kind)) is None:
            continue
        counts[kind] = count
        n, bare = count
        if n and bare == n:
            details += layer_details(db, slug, kind)
    return findings, counts, details
