"""Bring a map's staging tables to the shape `maps process insert` needs.

Each step reads a table's state and changes it only where it falls short, so a
map can be normalized any number of times, and `apply=False` reports the same
plan without writing. A map's staging tables are its own, so every step covers
the whole table.
"""

from dataclasses import dataclass, field

from psycopg.sql import SQL, Identifier

from macrostrat.database import Database
from macrostrat.map_utils.slugs import STAGING_KINDS, staging_table

from ..source_tables import COLUMN_SPECS
from ..utils import MapInfo, table_exists
from .fix_geometries import REPAIR

#: A single-part geometry column cannot hold the multi-part result of a repair.
MULTI = {"POLYGON": "MultiPolygon", "LINESTRING": "MultiLineString"}

#: Names that usually identify a feature in its source dataset, best first.
ID_NAMES = ("objectid", "fid", "ogc_fid", "gid", "id", "feature_id")

#: A column at least this distinct counts as an identifier.
NEARLY_UNIQUE = 0.99

_NUMERIC = ("smallint", "integer", "bigint", "numeric", "double precision", "real")
_INT4 = (-(2**31), 2**31 - 1)


@dataclass
class TableReport:
    table: str
    changes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class _Table:
    """A staging table as it stands, or as it will once prepared on a dry run."""

    ident: Identifier
    name: str
    kind: str
    columns: dict[str, str]
    geom: str
    #: Columns the prepare step adds, absent from the table on a dry run.
    pending: set[str] = field(default_factory=set)


def normalize(db: Database, map: MapInfo, *, apply: bool) -> list[TableReport]:
    """Normalize each of a map's staging tables; nothing is committed."""
    reports = []
    for kind in STAGING_KINDS:
        name = staging_table(map.slug, kind)
        if not table_exists(db, name, schema="sources"):
            continue
        report = TableReport(f"sources.{name}")
        reports.append(report)
        geom = _geometry_column(db, name)
        if geom is None:
            report.notes.append("no single geometry column to use as geom; skipped")
            continue
        t = _Table(Identifier("sources", name), name, kind, _columns(db, name), geom)
        _prepare(db, map, t, report, apply)
        _promote_geometry(db, t, report, apply)
        _repair(db, t, report, apply)
        _orig_id(db, t, report, apply)
    return reports


def _columns(db, name) -> dict[str, str]:
    return dict(
        db.run_query(
            "SELECT column_name, data_type FROM information_schema.columns"
            " WHERE table_schema = 'sources' AND table_name = :name",
            dict(name=name),
        ).all()
    )


def _geometry_column(db, name) -> str | None:
    """`geom`, or the table's only geometry column under another name."""
    names = (
        db.run_query(
            "SELECT f_geometry_column FROM geometry_columns"
            " WHERE f_table_schema = 'sources' AND f_table_name = :name",
            dict(name=name),
        )
        .scalars()
        .all()
    )
    if "geom" in names:
        return "geom"
    return names[0] if len(names) == 1 else None


def _prepare(db, map, t: _Table, report, apply):
    """The standard columns, `geom`, `_pkid` and `source_id`."""
    if t.geom != "geom":
        report.changes.append(f"rename {t.geom} → geom")
        if apply:
            _run(
                db,
                "ALTER TABLE {table} RENAME COLUMN {old} TO geom",
                t,
                old=Identifier(t.geom),
            )
            t.geom = "geom"

    if t.kind == "polygons" and "gid" in t.columns and "_pkid" not in t.columns:
        report.changes.append("rename gid → _pkid")
        if apply:
            _run(db, "ALTER TABLE {table} RENAME COLUMN gid TO _pkid", t)
        t.columns["_pkid"] = t.columns.pop("gid")

    missing = {
        c: type_ for c, type_ in COLUMN_SPECS[t.kind].items() if c not in t.columns
    }
    if missing:
        report.changes.append(f"add columns {', '.join(missing)}")
        for column, type_ in missing.items():
            if apply:
                _run(
                    db,
                    "ALTER TABLE {table} ADD COLUMN {column} {type}",
                    t,
                    column=Identifier(column),
                    type=SQL(type_),
                )
            else:
                t.pending.add(column)
            t.columns[column] = type_

    if "_pkid" not in t.columns:
        report.changes.append("add _pkid")
        if apply:
            _run(db, "ALTER TABLE {table} ADD COLUMN _pkid serial PRIMARY KEY", t)
        else:
            t.pending.add("_pkid")
        t.columns["_pkid"] = "integer"

    _fill(
        db,
        t,
        report,
        apply,
        "source_id",
        "source_id IS DISTINCT FROM :source_id",
        "source_id = :source_id",
        dict(source_id=map.id),
    )
    if t.kind == "polygons" and {"early_id", "late_id"} <= t.columns.keys():
        _fill(
            db,
            t,
            report,
            apply,
            "intervals from early_id, late_id",
            "t_interval IS NULL AND b_interval IS NULL"
            " AND (early_id IS NOT NULL OR late_id IS NOT NULL)",
            "t_interval = late_id, b_interval = early_id",
        )
    if t.kind == "polygons" and "ready" in t.columns:
        _fill(
            db,
            t,
            report,
            apply,
            "omit from ready",
            "omit IS NULL AND ready IS NOT NULL",
            "omit = NOT ready",
        )


def _fill(db, t: _Table, report, apply, what, where, assign, params=None):
    """Set `assign` on the rows matching `where`; a dry run only counts them."""
    params = params or {}
    n = db.run_query(
        f"SELECT count(*) FROM {{relation}} WHERE {where}",
        dict(params, relation=_relation(t)),
    ).scalar()
    if not n:
        return
    report.changes.append(f"set {what} on {n} rows")
    if apply:
        _run(db, f"UPDATE {{table}} SET {assign} WHERE {where}", t, **params)


def _relation(t: _Table):
    """The table, with any column a dry run has not added yet read as NULL."""
    if not t.pending:
        return t.ident
    nulls = SQL(", ").join(
        SQL("NULL::{} AS {}").format(SQL(t.columns[c]), Identifier(c))
        for c in sorted(t.pending)
    )
    return SQL("(SELECT *, {} FROM {}) AS s").format(nulls, t.ident)


def _promote_geometry(db, t: _Table, report, apply):
    row = db.run_query(
        "SELECT type, srid FROM geometry_columns"
        " WHERE f_table_schema = 'sources' AND f_table_name = :name"
        " AND f_geometry_column = :geom",
        dict(name=t.name, geom=t.geom),
    ).first()
    multi = MULTI.get(row.type) if row else None
    if multi is None:
        return
    report.changes.append(f"geom {row.type.lower()} → {multi.lower()}")
    if apply:
        _run(
            db,
            "ALTER TABLE {table} ALTER COLUMN geom"
            " TYPE geometry({multi}, {srid}) USING ST_Multi(geom)",
            t,
            multi=SQL(multi),
            srid=SQL(str(row.srid)),
        )


def _repair(db, t: _Table, report, apply):
    n = _run(
        db,
        "SELECT count(*) FROM {table} WHERE NOT ST_IsValid({geom})",
        t,
        geom=Identifier(t.geom),
    ).scalar()
    if not n:
        return
    report.changes.append(f"repair {n} invalid geometries")
    if apply:
        _run(
            db,
            "UPDATE {table} SET geom = {repair} WHERE NOT ST_IsValid(geom)",
            t,
            repair=SQL(REPAIR[t.kind]),
        )


def _orig_id(db, t: _Table, report, apply):
    n = _run(db, "SELECT count(*) FROM {table}", t).scalar()
    if not n:
        return
    if "orig_id" in t.columns and "orig_id" not in t.pending:
        set_ = _run(db, "SELECT count(orig_id) FROM {table}", t).scalar()
        if set_:
            if set_ < n:
                report.notes.append(f"orig_id set on {set_} of {n} rows")
            return

    candidates = [
        c
        for c, type_ in t.columns.items()
        if type_ in _NUMERIC
        and c not in COLUMN_SPECS[t.kind]
        and c != "_pkid"
        and c not in t.pending
    ]
    target_type = t.columns.get("orig_id", "integer")
    found = [
        s for s in _column_stats(db, t, candidates) if _qualifies(s, n, target_type)
    ]
    choice = _choose(found, n)
    if choice is None:
        if found:
            names = ", ".join(s["column"] for s in found)
            report.notes.append(f"orig_id is empty; {names} are equally plausible")
        else:
            report.notes.append(
                "orig_id is empty and no column obviously identifies features"
            )
        return

    share = (
        "unique"
        if choice["distinct"] == n
        else f"{choice['distinct'] / n:.1%} distinct"
    )
    report.changes.append(f"orig_id ← {choice['column']} ({share})")
    if apply:
        _run(
            db,
            "UPDATE {table} SET orig_id = CAST({column} AS {type})",
            t,
            column=Identifier(choice["column"]),
            type=SQL(target_type),
        )


def _run(db, sql, t: _Table, **params):
    return db.run_query(sql, dict(params, table=t.ident))


def _column_stats(db, t: _Table, columns) -> list[dict]:
    """Non-null, distinct and fractional counts and range of each column, in one scan."""
    if not columns:
        return []
    parts = []
    for i, c in enumerate(columns):
        col = '"' + c.replace('"', '""') + '"'
        parts.append(
            f"count({col}) AS n_{i}, count(DISTINCT {col}) AS d_{i},"
            f" count(*) FILTER (WHERE {col} <> trunc({col})) AS f_{i},"
            f" min({col})::float AS lo_{i}, max({col})::float AS hi_{i}"
        )
    row = _run(db, f"SELECT {', '.join(parts)} FROM {{table}}", t).one()._mapping
    return [
        dict(
            column=c,
            nonnull=row[f"n_{i}"],
            distinct=row[f"d_{i}"],
            fractional=row[f"f_{i}"],
            lo=row[f"lo_{i}"],
            hi=row[f"hi_{i}"],
        )
        for i, c in enumerate(columns)
    ]


def _qualifies(s: dict, n: int, target_type: str) -> bool:
    if s["nonnull"] < n or s["fractional"] or s["distinct"] < NEARLY_UNIQUE * n:
        return False
    if target_type == "integer":
        return _INT4[0] <= s["lo"] and s["hi"] <= _INT4[1]
    return True


def _choose(found: list[dict], n: int) -> dict | None:
    """The one obvious identifier: unique beats nearly so, then a familiar name."""
    if not found:
        return None
    unique = [s for s in found if s["distinct"] == n]
    pool = unique or found
    if len(pool) == 1:
        return pool[0]
    named = sorted(
        (s for s in pool if s["column"].lower() in ID_NAMES),
        key=lambda s: ID_NAMES.index(s["column"].lower()),
    )
    return named[0] if named else None
