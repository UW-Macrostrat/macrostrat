"""Write a set of maps to a Macrostrat map package."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from sqlalchemy import text

from macrostrat.database import Database

from ..utils.map_info import _MapInfo
from .format import Layer, dump_table, table_columns, write_manifest

console = Console(stderr=True)


@dataclass(frozen=True)
class TableSpec:
    """How one Postgres table is selected into the package."""

    layer: str
    table: str
    where: str
    order_by: Optional[str] = None
    # Columns that are database-specific or rebuilt by processing
    exclude: tuple[str, ...] = ()
    # Computed text columns, usually a slug standing in for an id
    extra: tuple[tuple[str, str], ...] = ()
    # For `sources.*` staging tables: the slug the table belongs to, or None
    # for a table shared by several maps
    owner: Optional[str] = None

    @property
    def is_staging(self) -> bool:
        return self.table.startswith("sources.")


def _slug_of(expr: str) -> str:
    return f"(SELECT s.slug FROM maps.sources s WHERE s.source_id = {expr})"


# Order matters only for readability; import follows its own order. Derived
# topology state (topogeometries, faces, `map_priority`, `map_topo`) is not
# exported: `macrostrat topo update` rebuilds it from `map_area` and
# `boundary_op` in the target.
TABLES = (
    TableSpec(
        "maps_sources",
        "maps.sources",
        "t.source_id = ANY(:ids)",
        "t.source_id",
        extra=(("superseded_by_slug", _slug_of("t.superseded_by")),),
    ),
    TableSpec(
        "polygons",
        "maps.polygons",
        "t.source_id = ANY(:ids)",
        # Materialized compilations last: their `orig_id`s name member polygons
        "t.source_id = ANY(:compilations), t.source_id, t.map_id",
    ),
    TableSpec(
        "lines", "maps.lines", "t.source_id = ANY(:ids)", "t.source_id, t.line_id"
    ),
    TableSpec(
        "points", "maps.points", "t.source_id = ANY(:ids)", "t.source_id, t.point_id"
    ),
    TableSpec("legend", "maps.legend", "t.source_id = ANY(:ids)", "t.legend_id"),
    TableSpec(
        "map_legend",
        "maps.map_legend",
        """t.legend_id IN (SELECT legend_id FROM maps.legend WHERE source_id = ANY(:ids))
        OR t.map_id IN (SELECT map_id FROM maps.polygons WHERE source_id = ANY(:ids))""",
    ),
    TableSpec(
        "ingest_process",
        "maps_metadata.ingest_process",
        "t.source_id = ANY(:ids)",
    ),
    TableSpec(
        "ingest_process_tag",
        "maps_metadata.ingest_process_tag",
        "t.source_id = ANY(:ids)",
    ),
    TableSpec(
        "map_area",
        "map_bounds.map_area",
        "t.id = ANY(:ids)",
        # `map_layer` is always the barrier layer, which the target seeds itself.
        exclude=("source_id", "topo", "geometry_hash", "topology_error", "map_layer"),
    ),
    TableSpec(
        "boundary_op",
        "map_bounds.boundary_op",
        "t.source_id = ANY(:ids)",
        "t.source_id, t.position",
        exclude=("id",),
    ),
    TableSpec(
        "compilation",
        "map_bounds.compilation",
        "t.source_id = ANY(:ids)",
        # A stamp of the member set's source ids, meaningless elsewhere
        exclude=("member_hash",),
    ),
    TableSpec(
        "compilation_member",
        "map_bounds.compilation_member",
        "t.compilation_id = ANY(:ids) OR t.member_id = ANY(:ids)",
        extra=(
            ("compilation_slug", _slug_of("t.compilation_id")),
            ("member_slug", _slug_of("t.member_id")),
        ),
    ),
)

STAGING_KINDS = ("polygons", "lines", "points")


def compilation_tree(db: Database, compilation: _MapInfo) -> list[int]:
    """A compilation and every map beneath it, at any depth."""
    return list(
        db.run_query(
            "SELECT :id UNION SELECT source_id FROM map_bounds.members_of(:id, true)",
            dict(id=compilation.id),
        ).scalars()
    )


def _staging_tables(conn, maps: list[_MapInfo], prefixes: set[str]) -> dict[str, str]:
    """`sources.*` tables holding these maps' staged data, mapped to their owner.

    Each map's own tables (by slug, or as recorded in `maps.sources`) are owned
    by it. A shared prefix (NGS stages 114 maps into `sources.ngs_*`) has no
    owner, and only rows for the exported maps are taken from it.
    """
    found = {}
    recorded = conn.execute(
        text(
            "SELECT slug, primary_table, primary_line_table FROM maps.sources"
            " WHERE source_id = ANY(:ids)"
        ),
        dict(ids=[m.id for m in maps]),
    ).all()
    for slug, *tables in recorded:
        for name in [*tables, *(f"{slug}_{k}" for k in STAGING_KINDS)]:
            if name is not None:
                found.setdefault(name, slug)
    for prefix in prefixes:
        for kind in STAGING_KINDS:
            found.setdefault(f"{prefix}_{kind}", None)
    return found


def export_maps(
    db: Database,
    path: Path,
    maps: list[_MapInfo],
    *,
    staging: bool = True,
    staging_prefixes: set[str] = frozenset(),
    metadata: Optional[dict] = None,
) -> list[Layer]:
    """Write `maps` and everything describing them to a new GeoPackage.

    The file is written beside `path` and moved into place once complete, so an
    interrupted export never leaves something that looks like a package.
    """
    path = Path(path)
    tmp = path.with_name(f".{path.stem}.partial.gpkg")
    tmp.unlink(missing_ok=True)
    try:
        layers = _export(db, tmp, maps, staging, staging_prefixes, metadata)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)
    return layers


def _export(db, tmp, maps, staging, staging_prefixes, metadata):
    with db.engine.connect() as conn:
        has_topology = table_columns(conn, "map_bounds.compilation_member") is not None
        layer_ids = set()
        if has_topology:
            layer_ids = set(
                conn.execute(
                    text(
                        "SELECT source_id FROM map_bounds.map_layer"
                        " WHERE source_id = ANY(:ids)"
                    ),
                    dict(ids=[m.id for m in maps]),
                ).scalars()
            )
        if layer_ids:
            # Every database seeds its own; edges to them travel by slug
            skipped = [m.slug for m in maps if m.id in layer_ids]
            console.print(f"[dim]Skipping map layers {', '.join(skipped)}[/]")
            maps = [m for m in maps if m.id not in layer_ids]
        if not maps:
            raise ValueError("No maps to export")

        ids = [m.id for m in maps]
        compilations = []
        if has_topology:
            compilations = list(
                conn.execute(
                    text(
                        "SELECT DISTINCT compilation_id FROM map_bounds.compilation_member"
                        " WHERE compilation_id = ANY(:ids)"
                    ),
                    dict(ids=ids),
                ).scalars()
            )
        params = dict(ids=ids, compilations=compilations)

        specs = list(TABLES)
        if staging:
            for table, owner in _staging_tables(conn, maps, staging_prefixes).items():
                specs.append(
                    TableSpec(
                        f"sources__{table}", f"sources.{table}", "true", owner=owner
                    )
                )

        layers = []
        for spec in specs:
            columns = table_columns(conn, spec.table)
            if columns is None:
                continue
            where = spec.where
            if spec.is_staging:
                if any(c.name == "source_id" for c in columns):
                    where = "t.source_id = ANY(:ids)"
                    if spec.owner is not None:
                        # Rows appended since `prepare-fields` are the owner's
                        where += " OR t.source_id IS NULL"
                elif spec.owner is None:
                    # A shared table we can't filter to these maps
                    continue
            layer = Layer(
                spec.layer,
                spec.table,
                [c for c in columns if c.name not in spec.exclude],
                owner=spec.owner,
            )
            dump_table(
                conn,
                tmp,
                layer,
                where,
                params,
                order_by=spec.order_by,
                extra=dict(spec.extra),
            )
            if layer.row_count == 0 and spec.is_staging:
                continue
            console.print(f"  [cyan]{layer.name}[/] [dim]{layer.row_count} rows[/]")
            layers.append(layer)

    meta = dict(
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        maps=[m.slug for m in maps],
        **(metadata or {}),
    )
    # `maps_sources` always has rows, so the GeoPackage exists by now
    write_manifest(tmp, meta, layers)
    return layers
