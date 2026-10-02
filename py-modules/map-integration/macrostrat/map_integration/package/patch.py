"""Patch parts of existing maps from a Macrostrat map package.

Where `ingest` creates or replaces whole maps, a patch changes only chosen
*elements* of maps the target already has, matched by slug. It is planned
first, read-only, so the whole set of changes can be reviewed and approved
before anything is written; the approved plan is applied in one transaction.

Each element decides what merging means for it:

- `metadata`: fields of `maps.sources`, merged -- a value the package lacks
  never clears one the target has.
- `boundary-ops`: a map's whole boundary operation stack, replaced.
"""

import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.markup import escape
from sqlalchemy import text

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database

from .format import Column, Package, insert_rows, quote, read_package, table_columns

console = Console(stderr=True)


@dataclass
class Target:
    slug: str
    package_id: int
    source_id: int


@dataclass
class Change:
    slug: str
    source_id: int
    element: str
    summary: str
    # Rich-formatted lines describing the change in detail
    details: list[str] = field(default_factory=list)
    data: Any = None


@dataclass
class PatchPlan:
    package: Package
    changes: list[Change] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Element:
    name: str
    # Package layers the element reads
    layers: tuple[str, ...]

    def plan(self, conn, pkg: Package, targets: list[Target], plan: PatchPlan):
        raise NotImplementedError

    def apply(self, conn, change: Change):
        raise NotImplementedError


# Descriptive fields only: identity, scale and serving state are left to ingest
METADATA_COLUMNS = (
    "name",
    "url",
    "ref_title",
    "authors",
    "ref_year",
    "ref_source",
    "ref_compilation",
    "isbn_doi",
    "license",
    "raster_url",
    "scale_denominator",
    "keywords",
    "language",
    "description",
)


class Metadata(Element):
    name = "metadata"
    layers = ("maps_sources",)

    def plan(self, conn, pkg, targets, plan):
        layer = pkg.layers["maps_sources"]
        cols = [
            c
            for c in table_columns(conn, "maps.sources")
            if c.name in METADATA_COLUMNS and layer.column(c.name)
        ]
        rows = {r["source_id"]: r for r in pkg.all_rows("maps_sources")}
        for t in targets:
            row = rows[t.package_id]
            # Merge: a field the package leaves empty keeps the target's value
            given = [c for c in cols if row.get(c.name) is not None]
            if not given:
                continue
            exprs = [
                f"CAST(t.{quote(c.name)} AS text) AS old_{i},"
                f" CAST(CAST(:p{i} AS {c.type}) AS text) AS new_{i}"
                for i, c in enumerate(given)
            ]
            params = {f"p{i}": row[c.name] for i, c in enumerate(given)}
            found = (
                conn.execute(
                    text(
                        f"SELECT {', '.join(exprs)} FROM maps.sources t"
                        " WHERE t.source_id = :id"
                    ),
                    dict(params, id=t.source_id),
                )
                .one()
                ._mapping
            )
            fields = {}
            details = []
            for i, c in enumerate(given):
                old, new = found[f"old_{i}"], found[f"new_{i}"]
                if old != new:
                    fields[c.name] = (c, row[c.name])
                    details.append(
                        f"{c.name}: [red]{escape(_short(old))}[/]"
                        f" → [green]{escape(_short(new))}[/]"
                    )
            if fields:
                plan.changes.append(
                    Change(
                        t.slug,
                        t.source_id,
                        self.name,
                        f"{len(fields)} field{'s' if len(fields) > 1 else ''}",
                        details,
                        fields,
                    )
                )

    def apply(self, conn, change):
        sets = ", ".join(
            f"{quote(name)} = CAST(:p{i} AS {c.type})"
            for i, (name, (c, _)) in enumerate(change.data.items())
        )
        params = {f"p{i}": v for i, (_, v) in enumerate(change.data.values())}
        conn.execute(
            text(f"UPDATE maps.sources SET {sets} WHERE source_id = :id"),
            dict(params, id=change.source_id),
        )


# Mirrors `map_topology.bounds.operations.COMPUTED_OPENINGS`
COMPUTED_OPENINGS = ("union", "compile", "world")


@dataclass(frozen=True)
class _Op:
    operation: str
    parameters: str  # canonical JSON
    note: Optional[str]
    # md5 of the operand geometry; None for a computed opening's cache, which
    # describes the environment it was computed in rather than an edit
    geometry: Optional[str]

    def label(self) -> str:
        parts = [self.operation]
        if self.parameters != "{}":
            parts.append(self.parameters)
        if self.geometry:
            parts.append("[geometry]")
        if self.note:
            parts.append(f"— {self.note}")
        return " ".join(parts)


def _op(operation, parameters, note, geometry_hash) -> _Op:
    """`parameters` as decoded JSON; a package's text form goes through `loads`."""
    if operation in COMPUTED_OPENINGS:
        geometry_hash = None
    return _Op(operation, json.dumps(parameters, sort_keys=True), note, geometry_hash)


class BoundaryOps(Element):
    name = "boundary-ops"
    layers = ("boundary_op",)

    def plan(self, conn, pkg, targets, plan):
        ids = [t.source_id for t in targets]
        with_area = set(
            conn.execute(
                text("SELECT id FROM map_bounds.map_area WHERE id = ANY(:ids)"),
                dict(ids=ids),
            ).scalars()
        )
        vocabulary = set(
            conn.execute(text("SELECT id FROM map_bounds.boundary_operation")).scalars()
        )
        current: dict[int, list[_Op]] = {i: [] for i in ids}
        for r in conn.execute(
            text(
                "SELECT source_id, operation, parameters, note,"
                " md5(ST_AsEWKB(geometry)) AS geometry"
                " FROM map_bounds.boundary_op WHERE source_id = ANY(:ids)"
                " ORDER BY source_id, position"
            ),
            dict(ids=ids),
        ):
            current[r.source_id].append(
                _op(r.operation, r.parameters, r.note, r.geometry)
            )

        rows = sorted(
            pkg.all_rows("boundary_op"), key=lambda r: (r["source_id"], r["position"])
        )
        hashes = conn.execute(
            text(
                "SELECT md5(ST_AsEWKB(CAST(g AS geometry)))"
                " FROM unnest(CAST(:g AS text[])) WITH ORDINALITY u(g, n) ORDER BY n"
            ),
            dict(g=[r["geometry"] for r in rows]),
        ).scalars()
        incoming: dict[int, list[tuple[dict, _Op]]] = {}
        for r, h in zip(rows, hashes):
            incoming.setdefault(r["source_id"], []).append(
                (r, _op(r["operation"], json.loads(r["parameters"]), r["note"], h))
            )

        for t in targets:
            new = incoming.get(t.package_id, [])
            ops = [o for _, o in new]
            if ops == current[t.source_id]:
                continue
            if t.source_id not in with_area:
                plan.warnings.append(
                    f"{t.slug}: no map_area in the target, so boundary operations"
                    " can't be attached; build its bounds first"
                )
                continue
            unknown = {o.operation for o in ops} - vocabulary
            if unknown:
                plan.warnings.append(
                    f"{t.slug}: the target has no boundary operation"
                    f" {', '.join(sorted(unknown))}; its stack is left as it is"
                )
                continue
            old = current[t.source_id]
            plan.changes.append(
                Change(
                    t.slug,
                    t.source_id,
                    self.name,
                    f"replace stack: {len(old)} → {len(ops)} ops",
                    _stack_diff(old, ops),
                    [r for r, _ in new],
                )
            )

    def apply(self, conn, change):
        params = dict(id=change.source_id)
        kept = conn.execute(
            text(
                "SELECT operation, parameters, CAST(geometry AS text) AS geometry"
                " FROM map_bounds.boundary_op WHERE source_id = :id AND position = 0"
            ),
            params,
        ).first()
        conn.execute(
            text("DELETE FROM map_bounds.boundary_op WHERE source_id = :id"), params
        )
        rows = [dict(r, source_id=change.source_id, error=None) for r in change.data]
        for r in rows:
            if r["position"] != 0 or r["operation"] not in COMPUTED_OPENINGS:
                continue
            # The target's own cache stands if the opening is unchanged; any
            # other is recomputed from the target's features on build
            r["geometry"] = None
            if kept is not None and _op(
                kept.operation, kept.parameters, None, None
            ) == _op(r["operation"], json.loads(r["parameters"]), None, None):
                r["geometry"] = kept.geometry
        cols = [
            c
            for c in table_columns(conn, "map_bounds.boundary_op")
            if not c.generated and c.name != "id"
        ]
        insert_rows(conn, "map_bounds.boundary_op", cols, rows)


def _stack_diff(old: list[_Op], new: list[_Op]) -> list[str]:
    lines = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=old, b=new).get_opcodes():
        if tag == "equal":
            lines += [f"[dim]  {escape(o.label())}[/]" for o in old[i1:i2]]
            continue
        lines += [f"[red]- {escape(o.label())}[/]" for o in old[i1:i2]]
        lines += [f"[green]+ {escape(o.label())}[/]" for o in new[j1:j2]]
    return lines


ELEMENTS: dict[str, Element] = {e.name: e for e in (Metadata(), BoundaryOps())}


def plan_patch(
    db: Database,
    path: Path,
    *,
    only: Optional[list[str]] = None,
    elements: Optional[list[str]] = None,
) -> PatchPlan:
    """Work out what applying a package's elements to the target would change.

    Reads only. A partial package offers just the elements it was exported
    with; a whole one offers every element, narrowed by `elements`.
    """
    pkg = read_package(path)
    offered = pkg.elements or list(ELEMENTS)
    chosen = elements or offered
    unknown = [e for e in chosen if e not in ELEMENTS]
    if unknown:
        raise MacrostratError(
            f"Unknown element {', '.join(unknown)}",
            details=f"Choose from {', '.join(ELEMENTS)}.",
        )
    absent = [e for e in chosen if e not in offered]
    if absent:
        raise MacrostratError(f"{path.name} doesn't carry {', '.join(absent)}")

    plan = PatchPlan(pkg)
    sources = pkg.all_rows("maps_sources")
    if only:
        sources = [s for s in sources if any(fnmatch(s["slug"], p) for p in only)]
        if not sources:
            raise MacrostratError(f"No maps in {path.name} match {', '.join(only)}")

    with db.engine.connect() as conn:
        existing = dict(
            conn.execute(
                text("SELECT slug, source_id FROM maps.sources WHERE slug = ANY(:s)"),
                dict(s=[s["slug"] for s in sources]),
            ).all()
        )
        targets = []
        for s in sources:
            if s["slug"] in existing:
                targets.append(Target(s["slug"], s["source_id"], existing[s["slug"]]))
            else:
                plan.missing.append(s["slug"])
        for name in chosen:
            element = ELEMENTS[name]
            if all(layer in pkg.layers for layer in element.layers):
                element.plan(conn, pkg, targets, plan)

    changed = {c.slug for c in plan.changes}
    plan.unchanged = [t.slug for t in targets if t.slug not in changed]
    plan.changes.sort(key=lambda c: (c.slug, list(ELEMENTS).index(c.element)))
    return plan


def apply_patch(db: Database, plan: PatchPlan):
    """Apply every change in an approved plan, or none of them."""
    with db.engine.begin() as conn:
        for change in plan.changes:
            ELEMENTS[change.element].apply(conn, change)
        _log(conn, plan)


def _log(conn, plan: PatchPlan):
    """Record each patched map's changes in `maps.source_operations`."""
    if table_columns(conn, "maps.source_operations") is None:
        return
    meta = plan.package.meta
    by_map: dict[int, list[Change]] = {}
    for c in plan.changes:
        by_map.setdefault(c.source_id, []).append(c)
    rows = [
        dict(
            source_id=source_id,
            operation="patch-package",
            app="macrostrat-cli",
            comments=f"Patched {', '.join(c.element for c in changes)}"
            f" from {plan.package.path.name}",
            details=json.dumps(
                dict(
                    package=plan.package.path.name,
                    exported_from=meta.get("exported_from"),
                    exported_at=meta.get("created"),
                    changes={c.element: c.summary for c in changes},
                )
            ),
        )
        for source_id, changes in by_map.items()
    ]
    cols = [
        Column("source_id", "integer", "integer"),
        Column("operation", "text", "text"),
        Column("app", "text", "text"),
        Column("comments", "text", "text"),
        Column("details", "jsonb", "text"),
    ]
    insert_rows(conn, "maps.source_operations", cols, rows)


def _short(value: Optional[str], width: int = 60) -> str:
    if value is None:
        return "∅"
    value = value.replace("\n", " ")
    return value if len(value) <= width else value[: width - 1] + "…"
