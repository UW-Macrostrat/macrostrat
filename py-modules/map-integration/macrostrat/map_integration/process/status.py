from pydantic import BaseModel
from rich import print
from rich.table import Table

from ..database import get_database
from ..utils import MapInfo, feature_counts
from ..utils.map_info import MapSelector, resolve_maps


class MapProcessingStep(BaseModel):
    name: str
    description: str
    completed: bool = False
    details: str = ""


class MapIssue(BaseModel):
    name: str
    description: str


class MapProcessingTable(Table):
    def __init__(self, map: MapInfo):
        super().__init__(title="Processing")
        self.add_column("Step", justify="right", style="cyan", no_wrap=True)
        self.add_column("Completed", justify="right", style="cyan", no_wrap=True)
        self.add_column("Details")
        self.add_column("Description", style="dim")

    def add_step(self, step: MapProcessingStep):
        self.add_row(
            step.name, "✅" if step.completed else "❌", step.description, step.details
        )


def processing_status(maps: MapSelector):
    """Get the processing status for the selected map sources."""
    db = get_database()
    selected = resolve_maps(db, maps)
    if len(selected) == 1:
        _status_detail(db, selected[0])
    else:
        _status_summary(db, selected)


def _status_detail(db, map_info: MapInfo):
    """The per-step view of one map, with the issues found for it."""
    source_id = map_info.id
    geoms = _geometry_flags(db, [source_id])[source_id]

    print(f"Source ID: {source_id}")

    table = MapProcessingTable(map_info)

    counts = feature_counts(db, map_info)
    total = counts.n_polygons + counts.n_lines + counts.n_points
    has_data = total > 0

    issues = []

    if counts.n_polygons == 0 and has_data:
        issues.append(MapIssue(name="No polygons", description="No map polygons found"))

    steps = [
        MapProcessingStep(
            name="insert",
            description="Insert the source into the maps schema",
            completed=has_data,
            details=f"Polygons: {counts.n_polygons}, Lines: {counts.n_lines}, Points: {counts.n_points}",
        ),
        MapProcessingStep(
            name="web-geom",
            description="Create a geometry for use on the web",
            completed=geoms.has_web_geom,
        ),
        MapProcessingStep(
            name="rgeom",
            description="Create a unioned reference geometry",
            completed=geoms.has_rgeom,
        ),
    ]

    for step in steps:
        table.add_step(step)

    print(table)

    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"[yellow bold]{issue.name}[/bold]: [yellow dim]{issue.description}")


def _status_summary(db, selected: list[MapInfo]):
    """One row per map, for the case a glob selects a whole compilation.

    The detail view is three queries a map, which over `ngs-*` is several hundred
    round trips to render 114 tables nobody can read at once. This asks the same
    questions once, and what the reader wants from a sweep is which maps are
    missing a step -- so that is a column, and a tally, rather than a table each.
    """
    rows = db.run_query(
        """
        WITH selected AS (
          SELECT unnest(:ids::integer[]) AS source_id
        ),
        polygons AS (
          SELECT source_id, count(*) AS n FROM maps.polygons
          WHERE source_id = ANY(:ids) GROUP BY source_id
        ),
        lines AS (
          SELECT source_id, count(*) AS n FROM maps.lines
          WHERE source_id = ANY(:ids) GROUP BY source_id
        ),
        points AS (
          SELECT source_id, count(*) AS n FROM maps.points
          WHERE source_id = ANY(:ids) GROUP BY source_id
        )
        SELECT
          s.source_id,
          s.slug,
          coalesce(polygons.n, 0) AS n_polygons,
          coalesce(lines.n, 0) AS n_lines,
          coalesce(points.n, 0) AS n_points,
          s.web_geom IS NOT NULL AS has_web_geom,
          s.rgeom IS NOT NULL AS has_rgeom,
          -- A compilation holds no polygons of its own unless it has been
          -- materialized, so "insert" is not a step it is missing. `to_regclass`
          -- because `map_bounds` belongs to the topology module, which a
          -- map-integration install does not require.
          coalesce(
            to_regclass('map_bounds.compilation') IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM map_bounds.compilation c
                WHERE c.source_id = s.source_id
              ),
            false
          ) AS is_compilation
        FROM selected
        JOIN maps.sources s USING (source_id)
        LEFT JOIN polygons USING (source_id)
        LEFT JOIN lines USING (source_id)
        LEFT JOIN points USING (source_id)
        ORDER BY s.source_id
        """,
        dict(ids=[m.id for m in selected]),
    ).all()

    table = Table(title=f"Processing status ({len(rows)} maps)")
    table.add_column("Map", style="cyan", no_wrap=True)
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Poly", justify="right")
    table.add_column("Lines", justify="right")
    table.add_column("Pts", justify="right")
    table.add_column("web", justify="center")
    table.add_column("rgeom", justify="center")

    incomplete = []
    for row in rows:
        has_data = row.n_polygons + row.n_lines + row.n_points > 0
        missing = []
        if not has_data and not row.is_compilation:
            missing.append("insert")
        if not row.has_web_geom:
            missing.append("web-geom")
        if not row.has_rgeom and not row.is_compilation:
            missing.append("rgeom")
        if missing:
            incomplete.append((row.slug, missing))

        polygons = f"{row.n_polygons:,}"
        if not row.n_polygons:
            # Zero is expected of a virtual compilation and a defect anywhere
            # else, so it is only worth colouring in the second case.
            polygons = "[dim]--[/]" if row.is_compilation else "[red]0[/]"

        label = row.slug
        if row.is_compilation:
            label = f"{row.slug} [dim](compilation)[/]"

        table.add_row(
            label,
            str(row.source_id),
            polygons,
            f"{row.n_lines:,}",
            f"{row.n_points:,}",
            "✅" if row.has_web_geom else "❌",
            "✅" if row.has_rgeom else "❌",
        )

    print(table)

    if not incomplete:
        print(f"\n[green]All {len(rows)} maps complete")
        return

    print(f"\n[yellow]{len(incomplete)} of {len(rows)} maps have steps outstanding")
    by_step: dict[str, list[str]] = {}
    for slug, missing in incomplete:
        for step in missing:
            by_step.setdefault(step, []).append(slug)
    for step, slugs in by_step.items():
        print(f"  [yellow bold]{step}[/]: [dim]{len(slugs)} maps")


class _GeometryFlags(BaseModel):
    has_web_geom: bool
    has_rgeom: bool


def _geometry_flags(db, source_ids: list[int]) -> dict[int, _GeometryFlags]:
    rows = db.run_query(
        """
        SELECT source_id, web_geom IS NOT NULL AS has_web_geom,
               rgeom IS NOT NULL AS has_rgeom
        FROM maps.sources WHERE source_id = ANY(:ids)
        """,
        dict(ids=source_ids),
    ).all()
    return {
        r.source_id: _GeometryFlags(has_web_geom=r.has_web_geom, has_rgeom=r.has_rgeom)
        for r in rows
    }
