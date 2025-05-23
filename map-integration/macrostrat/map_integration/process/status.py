from psycopg2.sql import Identifier
from pydantic import BaseModel
from rich import print
from rich.table import Table

from ..database import get_database
from ..utils import MapInfo, feature_counts


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


def processing_status(map: MapInfo):
    """Get the processing status for a source."""
    db = get_database()
    map_info = map
    source_id = map_info.id
    if map_info is None:
        raise ValueError(f"No source found with slug {map_info.slug}")

    # Check if the source_id exists
    has_webgeom = _has_field(source_id, "web_geom")
    has_rgeom = _has_field(source_id, "rgeom")

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
            completed=has_webgeom,
        ),
        MapProcessingStep(
            name="rgeom",
            description="Create a unioned reference geometry",
            completed=has_rgeom,
        ),
    ]

    for step in steps:
        table.add_step(step)

    print(table)

    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"[yellow bold]{issue.name}[/bold]: [yellow dim]{issue.description}")


def _has_field(source_id: int, field_name: str) -> bool:
    db = get_database()
    return db.run_query(
        "SELECT {field_name} IS NOT NULL FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source_id, "field_name": Identifier(field_name)},
    ).scalar()
