"""Load a Macrostrat map package into a database.

Maps are matched by slug, the one key that means the same thing everywhere;
every serial id (`source_id`, `map_id`, `legend_id`, ...) is drawn afresh from
the target's own sequences and the package's references are rewritten to suit.

The whole import is one transaction. The map itself -- `maps.sources`, its
features and its legend -- must load or nothing does. Everything else is
context that may be stale or may not fit the target's schema (an ingest state
the target doesn't know, a compilation cycle, a staging table with odd types),
so each of those tables loads under its own savepoint and falls back to
row-by-row, reporting what it dropped rather than failing the map.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Iterable, Optional

from click import ClickException
from rich.console import Console
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database
from macrostrat.map_utils.slugs import slug_forms

from .format import (
    Column,
    Layer,
    Package,
    insert_rows,
    qualified,
    quote,
    read_package,
    table_columns,
)

console = Console(stderr=True)


class ConflictAction(str, Enum):
    ask = "ask"
    overwrite = "overwrite"
    skip = "skip"
    stop = "stop"


class ImportStopped(MacrostratError, ClickException):
    """An import stopped before writing anything.

    A `ClickException` so the CLI reports it rather than printing a traceback.
    """

    exit_code = 1

    def __init__(self, message: str, details: Optional[str] = None):
        MacrostratError.__init__(self, message, details)

    def format_message(self) -> str:
        return "\n".join(filter(None, [self.message, self.details]))


# Given a slug already in the target, decide what to do with it
ConflictResolver = Callable[[str], ConflictAction]


@dataclass
class ImportReport:
    imported: dict[str, int] = field(default_factory=dict)  # slug -> source_id
    overwritten: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def warn(self, message: str):
        self.warnings.append(message)
        console.print(f"[yellow]warning[/] {message}")


def import_package(
    db: Database,
    path: Path,
    *,
    on_conflict: ConflictAction = ConflictAction.ask,
    resolve: Optional[ConflictResolver] = None,
    only: Optional[list[str]] = None,
    staging: bool = True,
) -> ImportReport:
    """Import the maps in a package, optionally only slugs matching `only` globs.

    A slug already present in the target is handled per `on_conflict`; `ask`
    defers to `resolve`, called once per conflicting slug before anything is
    written, so stopping leaves the target untouched. Overwriting keeps the
    target's `source_id` and replaces the map's data in place.
    """
    pkg = read_package(path)
    if pkg.elements is not None:
        raise ImportStopped(
            f"{Path(path).name} holds only {', '.join(pkg.elements)} for existing maps",
            details="Apply it with `macrostrat maps patch`.",
        )
    sources = pkg.all_rows("maps_sources")
    if only:
        sources = [
            s
            for s in sources
            if any(fnmatch(s["slug"], v) for p in only for v in slug_forms(p))
        ]
        if not sources:
            raise MacrostratError(f"No maps in {path.name} match {', '.join(only)}")

    report = ImportReport()
    with db.engine.connect() as conn:
        existing = dict(
            conn.execute(
                text("SELECT slug, source_id FROM maps.sources WHERE slug = ANY(:s)"),
                dict(s=[s["slug"] for s in sources]),
            ).all()
        )

    plan = []
    for row in sources:
        target_id = existing.get(row["slug"])
        if target_id is not None:
            action = on_conflict
            if action == ConflictAction.ask:
                if resolve is None:
                    raise ImportStopped(
                        f"Map {row['slug']!r} already exists in the target",
                        details="Choose an --on-conflict action to import non-interactively.",
                    )
                action = resolve(row["slug"])
            if action == ConflictAction.stop:
                raise ImportStopped(f"Stopped at existing map {row['slug']!r}")
            if action == ConflictAction.skip:
                report.skipped.append(row["slug"])
                continue
            report.overwritten.append(row["slug"])
        plan.append((row, target_id))

    if not plan:
        console.print("Nothing to import")
        return report

    with db.engine.begin() as conn:
        _Importer(conn, pkg, report, staging=staging).run(plan)
    return report


# Tables whose rows are keyed on a map's polygons and would be orphaned when an
# overwrite replaces them. Processing rebuilds all of these.
_PER_POLYGON = (
    "maps.map_liths",
    "maps.map_units",
    "maps.lookup",
)


class _Importer:
    def __init__(self, conn, pkg: Package, report: ImportReport, *, staging: bool):
        self.conn = conn
        self.pkg = pkg
        self.report = report
        self.staging = staging
        self._tables: dict[str, Optional[list[Column]]] = {}
        # Package id -> target id
        self.source_ids: dict[int, int] = {}
        self.map_ids: dict[int, int] = {}
        self.legend_ids: dict[int, int] = {}

    # Plumbing

    def target(self, table: str) -> Optional[list[Column]]:
        if table not in self._tables:
            self._tables[table] = table_columns(self.conn, table)
        return self._tables[table]

    def has(self, layer: str) -> bool:
        """Whether the package carries a layer the target can take."""
        spec = self.pkg.layers.get(layer)
        return spec is not None and self.target(spec.table) is not None

    def common(self, layer: str, *, skip: Iterable[str] = ()) -> list[Column]:
        """Target columns the package also has, less `skip`."""
        spec = self.pkg.layers[layer]
        target = {c.name: c for c in self.target(spec.table) if not c.generated}
        skip = set(skip)
        missing = [
            c.name for c in spec.columns if c.name not in target and c.name not in skip
        ]
        if missing:
            self.report.warn(
                f"{spec.table} has no column {', '.join(missing)}; dropped from import"
            )
        return [
            target[c.name]
            for c in spec.columns
            if c.name in target and c.name not in skip
        ]

    def insert(self, table: str, columns: list[Column], rows: list[dict], suffix=""):
        insert_rows(self.conn, table, columns, rows, suffix)

    def allocate(self, table: str, column: str, n: int) -> list[int]:
        """Draw `n` ids from the sequence behind a column's default."""
        default = next(c.default for c in self.target(table) if c.name == column)
        if default is None:
            raise MacrostratError(f"{table}.{column} has no default to draw ids from")
        return list(
            self.conn.execute(
                text(f"SELECT {default} FROM generate_series(1, :n) ORDER BY 1"),
                dict(n=n),
            ).scalars()
        )

    def tolerant(self, label: str, rows: list[dict], load: Callable[[list], None]):
        """Load `rows`, falling back to one savepoint per row on failure."""
        if not rows:
            return 0
        try:
            with self.conn.begin_nested():
                load(rows)
            return len(rows)
        except DBAPIError:
            pass
        errors = []
        for row in rows:
            try:
                with self.conn.begin_nested():
                    load([row])
            except DBAPIError as err:
                errors.append(err)
        if errors:
            self.report.warn(
                f"{label}: skipped {len(errors)} of {len(rows)} rows"
                f" ({_reason(errors[0])})"
            )
        return len(rows) - len(errors)

    def count(self, layer: str, n: int):
        self.report.counts[layer] = self.report.counts.get(layer, 0) + n

    # The import

    def run(self, plan: list[tuple[dict, Optional[int]]]):
        self.load_sources(plan)
        self.slugs = {row["slug"] for row, _ in plan}
        overwritten = [t for _, t in plan if t is not None]
        if overwritten:
            self.clear(overwritten)

        # Derived compilations hold polygons but no legend: theirs point at
        # their members' polygons through `orig_id`
        compilations = self.pkg.distinct("compilation_member", "compilation_id")
        derived = compilations - self.pkg.distinct("legend", "source_id")
        self.load_features("polygons", "map_id", self.map_ids, derived)
        self.load_features("lines", "line_id")
        self.load_features("points", "point_id")
        self.load_features("legend", "legend_id", self.legend_ids)
        self.load_map_legend()

        if self.staging:
            for layer in self.pkg.layers.values():
                if layer.table.startswith("sources."):
                    self.load_staging(layer)

        self.load_simple(
            "ingest_process", conflict=("source_id",), prepare=self._ingest_states
        )
        self.load_simple("ingest_process_tag", conflict=("source_id", "tag"))
        # Edges before bounds: the `rgeom` mirror skips maps that have members
        self.load_simple("compilation", conflict=("source_id",))
        self.load_compilation_members()
        self.load_map_area()
        self.load_simple("boundary_op", source_column="source_id")
        self.link_superseded()
        self.log_operation()

        for layer, n in self.report.counts.items():
            console.print(f"  [cyan]{layer}[/] [dim]{n} rows[/]")

    def load_sources(self, plan):
        # `rgeom` in older packages: only the `map_area` trigger writes it.
        cols = self.common(
            "maps_sources",
            skip=("source_id", "superseded_by", "superseded_by_slug", "rgeom"),
        )
        names = [c.name for c in cols]
        values = [f"CAST(:p{i} AS {c.type})" for i, c in enumerate(cols)]
        for row, target_id in plan:
            params = {f"p{i}": row.get(c.name) for i, c in enumerate(cols)}
            if target_id is None:
                target_id = self.conn.execute(
                    text(
                        f"INSERT INTO maps.sources ({', '.join(map(quote, names))})"
                        f" VALUES ({', '.join(values)}) RETURNING source_id"
                    ),
                    params,
                ).scalar()
            else:
                sets = ", ".join(f"{quote(n)} = {v}" for n, v in zip(names, values))
                self.conn.execute(
                    text(f"UPDATE maps.sources SET {sets} WHERE source_id = :id"),
                    dict(params, id=target_id),
                )
            self.source_ids[row["source_id"]] = target_id
            self.report.imported[row["slug"]] = target_id
        self.count("maps_sources", len(plan))

    def clear(self, ids: list[int]):
        """Remove an overwritten map's data, for the layers the package carries."""
        polygons = "SELECT map_id FROM maps.polygons WHERE source_id = ANY(:ids)"
        legends = "SELECT legend_id FROM maps.legend WHERE source_id = ANY(:ids)"
        stmts = [
            f"DELETE FROM {t} WHERE map_id IN ({polygons})"
            for t in _PER_POLYGON
            if self.target(t) is not None
        ]
        stmts += [
            f"DELETE FROM maps.map_legend WHERE legend_id IN ({legends})"
            f" OR map_id IN ({polygons})",
            f"DELETE FROM maps.legend_liths WHERE legend_id IN ({legends})",
            "DELETE FROM maps.legend WHERE source_id = ANY(:ids)",
            "DELETE FROM maps.polygons WHERE source_id = ANY(:ids)",
            "DELETE FROM maps.lines WHERE source_id = ANY(:ids)",
            "DELETE FROM maps.points WHERE source_id = ANY(:ids)",
        ]
        if self.pkg.layers["maps_sources"].column("superseded_by_slug"):
            stmts.append(
                "UPDATE maps.sources SET superseded_by = NULL WHERE source_id = ANY(:ids)"
            )
        # The package is authoritative for these where it has them. Ingest
        # process rows are upserted instead, which keeps their `map_files`.
        if self.has("ingest_process_tag"):
            stmts.append(
                "DELETE FROM maps_metadata.ingest_process_tag WHERE source_id = ANY(:ids)"
            )
        if self.has("boundary_op"):
            stmts.append(
                "DELETE FROM map_bounds.boundary_op WHERE source_id = ANY(:ids)"
            )
        if self.has("compilation_member"):
            # Membership *of* these compilations; their own placements elsewhere
            # are upserted, so the target's other compilations keep them
            stmts.append(
                "DELETE FROM map_bounds.compilation_member WHERE compilation_id = ANY(:ids)"
            )
        for sql in stmts:
            self.conn.execute(text(sql), dict(ids=ids))

    def load_features(self, layer, id_column, id_map=None, derived=()):
        if not self.has(layer):
            return
        table = self.pkg.layers[layer].table
        cols = self.common(layer)
        assign = any(c.name == id_column for c in cols)
        for chunk in self.pkg.rows(layer):
            chunk = [r for r in chunk if r["source_id"] in self.source_ids]
            new_ids = self.allocate(table, id_column, len(chunk)) if assign else []
            for i, row in enumerate(chunk):
                if row["source_id"] in derived:
                    self._remap_orig_id(row)
                row["source_id"] = self.source_ids[row["source_id"]]
                if assign:
                    if id_map is not None:
                        id_map[row[id_column]] = new_ids[i]
                    row[id_column] = new_ids[i]
            self.insert(table, cols, chunk)
            self.count(layer, len(chunk))

    def _remap_orig_id(self, row):
        """Point a derived compilation's polygon at its member's new `map_id`.

        Members' polygons come first in the package, so they are mapped by now.
        """
        orig = row.get("orig_id")
        if orig and orig.isdigit() and int(orig) in self.map_ids:
            row["orig_id"] = str(self.map_ids[int(orig)])

    def load_map_legend(self):
        if not self.has("map_legend"):
            return
        rows, orphans = [], 0
        for row in self.pkg.all_rows("map_legend"):
            legend_id = self.legend_ids.get(row["legend_id"])
            map_id = self.map_ids.get(row["map_id"])
            if legend_id is None or map_id is None:
                # Half a link means the other half was left behind
                orphans += (legend_id is None) != (map_id is None)
                continue
            rows.append(dict(legend_id=legend_id, map_id=map_id))
        if orphans:
            self.report.warn(
                f"map_legend: {orphans} rows link to a polygon or legend not imported"
            )
        cols = self.common("map_legend")
        self.count(
            "map_legend",
            self.tolerant(
                "map_legend",
                rows,
                lambda r: self.insert(
                    "maps.map_legend", cols, r, "ON CONFLICT DO NOTHING"
                ),
            ),
        )

    def _remapped(self, layer: str, source_column: str) -> list[dict]:
        rows = []
        for row in self.pkg.all_rows(layer):
            if row[source_column] in self.source_ids:
                row[source_column] = self.source_ids[row[source_column]]
                rows.append(row)
        return rows

    def load_simple(
        self, layer, *, source_column="source_id", conflict=(), prepare=None
    ):
        """A table keyed on the map: remap its source id and upsert."""
        if not self.has(layer):
            return
        spec = self.pkg.layers[layer]
        cols = self.common(layer)
        suffix = ""
        if conflict:
            updates = [c.name for c in cols if c.name not in conflict]
            suffix = f"ON CONFLICT ({', '.join(map(quote, conflict))}) " + (
                "DO UPDATE SET "
                + ", ".join(f"{quote(n)} = EXCLUDED.{quote(n)}" for n in updates)
                if updates
                else "DO NOTHING"
            )
        rows = self._remapped(layer, source_column)
        if prepare is not None:
            prepare(rows)
        n = self.tolerant(
            layer, rows, lambda r: self.insert(spec.table, cols, r, suffix)
        )
        self.count(layer, n)

    def _ingest_states(self, rows):
        """Keep a process whose state the target doesn't define, without it."""
        known = set(
            self.conn.execute(
                text("SELECT id FROM maps_metadata.ingest_state")
            ).scalars()
        )
        for row in rows:
            if row.get("state") is not None and row["state"] not in known:
                self.report.warn(
                    f"ingest_process: state {row['state']!r} is not defined here;"
                    f" left empty for source {row['source_id']}"
                )
                row["state"] = None

    def load_compilation_members(self):
        if not self.has("compilation_member"):
            return
        rows = self.pkg.all_rows("compilation_member")
        slugs = {r[k] for r in rows for k in ("compilation_slug", "member_slug")}
        ids = dict(
            self.conn.execute(
                text("SELECT slug, source_id FROM maps.sources WHERE slug = ANY(:s)"),
                dict(s=list(slugs)),
            ).all()
        )
        edges, unresolved = [], 0
        for row in rows:
            # Only edges touching a map that is actually being imported
            if not {row["compilation_slug"], row["member_slug"]} & self.slugs:
                continue
            compilation = ids.get(row["compilation_slug"])
            member = ids.get(row["member_slug"])
            if compilation is None or member is None:
                unresolved += 1
                continue
            edges.append(dict(row, compilation_id=compilation, member_id=member))
        if unresolved:
            self.report.warn(
                f"compilation_member: {unresolved} edges name a map not in the target"
            )
        cols = self.common(
            "compilation_member", skip=("compilation_slug", "member_slug")
        )
        suffix = "ON CONFLICT (compilation_id, member_id) DO UPDATE SET priority = EXCLUDED.priority"
        self.count(
            "compilation_member",
            self.tolerant(
                "compilation_member",
                edges,
                lambda r: self.insert("map_bounds.compilation_member", cols, r, suffix),
            ),
        )

    def load_map_area(self):
        """Boundaries, upserted so an overwrite keeps its topology references.

        Changing the geometry clears `geometry_hash`, which queues the map for
        re-noding on the next `macrostrat topo update`.
        """
        if not self.has("map_area"):
            return
        # Packages written before layers were keyed by compilation carry the
        # layer's slug, which nothing reads any more.
        cols = self.common("map_area", skip=("map_layer_slug",))
        rows = self._remapped("map_area", "id")
        # Every map's boundary is recorded in the barrier layer, which each
        # database seeds as its own, so it is the target's rather than carried.
        barrier = self.conn.execute(
            text(
                "SELECT CASE WHEN to_regprocedure('map_bounds.barrier_layer()')"
                " IS NOT NULL THEN map_bounds.barrier_layer() END"
            )
        ).scalar()
        if barrier is not None:
            cols.append(
                next(
                    c
                    for c in self.target("map_bounds.map_area")
                    if c.name == "map_layer"
                )
            )
            for row in rows:
                row["map_layer"] = barrier
        updates = ", ".join(
            f"{quote(c.name)} = EXCLUDED.{quote(c.name)}"
            for c in cols
            if c.name != "id"
        )
        suffix = f"ON CONFLICT (id) DO UPDATE SET {updates}"
        n = self.tolerant(
            "map_area",
            rows,
            lambda r: self.insert("map_bounds.map_area", cols, r, suffix),
        )
        self.count("map_area", n)

    def load_staging(self, layer: Layer):
        """Recreate a map's `sources.*` staging table, or merge into a shared one."""
        if layer.owner is not None and layer.owner not in self.slugs:
            return
        has_source = layer.column("source_id") is not None
        rows = []
        for chunk in self.pkg.rows(layer.name):
            for row in chunk:
                if has_source and row["source_id"] is not None:
                    if row["source_id"] not in self.source_ids:
                        continue
                    row["source_id"] = self.source_ids[row["source_id"]]
                rows.append(row)
        if not rows:
            return
        table = layer.table
        ids = list(self.source_ids.values())
        try:
            with self.conn.begin_nested():
                replace = layer.owner is not None or self.target(table) is None
                if not replace and has_source:
                    others = self.conn.execute(
                        text(
                            f"SELECT EXISTS (SELECT 1 FROM {qualified(table)}"
                            " WHERE source_id IS NULL OR NOT source_id = ANY(:ids))"
                        ),
                        dict(ids=ids),
                    ).scalar()
                    replace = not others
                if replace:
                    self._create_staging_table(layer)
                    cols = layer.columns
                else:
                    self.conn.execute(
                        text(
                            f"DELETE FROM {qualified(table)} WHERE source_id = ANY(:ids)"
                        ),
                        dict(ids=ids),
                    )
                    cols = self.common(layer.name, skip=("_pkid",))
                self.insert(table, cols, rows)
                if replace and layer.column("_pkid"):
                    self.conn.execute(
                        text(
                            "SELECT setval(pg_get_serial_sequence(:t, '_pkid'),"
                            f" (SELECT max(_pkid) FROM {qualified(table)}))"
                        ),
                        dict(t=qualified(table)),
                    )
            self.count(layer.name, len(rows))
        except DBAPIError as err:
            self._tables.pop(table, None)
            self.report.warn(f"{table}: not imported ({_reason(err)})")

    def _create_staging_table(self, layer: Layer):
        table = qualified(layer.table)
        defs = [
            f"{quote(c.name)} serial PRIMARY KEY"
            if c.name == "_pkid"
            else f"{quote(c.name)} {c.type}"
            for c in layer.columns
        ]
        self.conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        self.conn.execute(text(f"CREATE TABLE {table} ({', '.join(defs)})"))
        if layer.geometry_column:
            self.conn.execute(
                text(
                    f"CREATE INDEX ON {table} USING gist ({quote(layer.geometry_column)})"
                )
            )
        self._tables.pop(layer.table, None)

    def link_superseded(self):
        rows = [
            r
            for r in self.pkg.all_rows("maps_sources")
            if r.get("superseded_by_slug") and r["source_id"] in self.source_ids
        ]

        def link(rows):
            for r in rows:
                found = self.conn.execute(
                    text(
                        "UPDATE maps.sources SET superseded_by ="
                        " (SELECT source_id FROM maps.sources WHERE slug = :by)"
                        " WHERE source_id = :id RETURNING superseded_by"
                    ),
                    dict(
                        by=r["superseded_by_slug"], id=self.source_ids[r["source_id"]]
                    ),
                ).scalar()
                if found is None:
                    raise _Unresolved(r["superseded_by_slug"])

        for r in rows:
            try:
                with self.conn.begin_nested():
                    link([r])
            except (DBAPIError, _Unresolved) as err:
                self.report.warn(
                    f"{r['slug']} is superseded by {r['superseded_by_slug']!r},"
                    f" which could not be linked ({_reason(err)})"
                )

    def log_operation(self):
        """Record where each map came from in `maps.source_operations`."""
        if self.target("maps.source_operations") is None:
            return
        meta = self.pkg.meta
        rows = [
            dict(
                source_id=target_id,
                operation="import-package",
                app="macrostrat-cli",
                comments=f"Imported from {self.pkg.path.name}",
                details=json.dumps(
                    dict(
                        package=self.pkg.path.name,
                        exported_from=meta.get("exported_from"),
                        exported_at=meta.get("created"),
                        package_source_id=package_id,
                    )
                ),
            )
            for package_id, target_id in self.source_ids.items()
        ]
        cols = [
            Column("source_id", "integer", "integer"),
            Column("operation", "text", "text"),
            Column("app", "text", "text"),
            Column("comments", "text", "text"),
            Column("details", "jsonb", "text"),
        ]
        self.tolerant(
            "source_operations",
            rows,
            lambda r: self.insert("maps.source_operations", cols, r),
        )


class _Unresolved(Exception):
    def __str__(self):
        return f"no map {self.args[0]!r} in the target"


def _reason(err: Exception) -> str:
    orig = getattr(err, "orig", err)
    return str(orig).strip().splitlines()[0]
