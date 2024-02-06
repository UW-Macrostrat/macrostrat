from psycopg2.sql import Identifier
from rich import print
from rich.columns import Columns
from rich.table import Column, Table
from typer import Argument

from ..database import db
from ..utils import MapInfo, get_map_info


def complete_map_slugs(incomplete: str):
    return (
        db.run_query(
            "SELECT slug FROM maps.sources WHERE slug ILIKE :incomplete",
            {"incomplete": f"{incomplete}%"},
        )
        .scalars()
        .all()
    )


def processing_status(
    identifier: str = Argument(
        help="Autocompleted map ID", autocompletion=complete_map_slugs
    )
):
    """Get the processing status for a source."""
    info = get_map_info(db, identifier)
    source_id = info.id
    if info is None:
        raise ValueError(f"No source found with slug {identifier}")

    # Check if the source_id exists
    has_webgeom = _has_field(source_id, "web_geom")
    has_rgeom = _has_field(source_id, "rgeom")

    print(f"Source ID: {source_id}")

    table = Table(
        "Step",
        "Completed",
        "Description",
        title="Processing",
    )

    table.add_row(
        "web-geom", "✅" if has_webgeom else "❌", "Create a geometry for use on the web"
    )
    table.add_row(
        "rgeom",
        "✅" if has_rgeom else "❌",
        "Create a unioned reference geometry",
    )

    print(table)


def _has_field(source_id: int, field_name) -> bool:
    return db.run_query(
        "SELECT {field_name} IS NOT NULL FROM maps.sources WHERE source_id = :source_id",
        {"source_id": source_id, "field_name": Identifier(field_name)},
    ).scalar()
