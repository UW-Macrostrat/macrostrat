from typing import Optional

from macrostrat.database import Database
from psycopg2.sql import Identifier
from pydantic import BaseModel
from typer import Argument
from typing_extensions import Annotated

from macrostrat.core import app
from macrostrat.core.exc import MacrostratError

from ..database import db
from ._database import table_exists


class _MapInfo(BaseModel):
    """Basic information about a map."""

    id: int
    slug: str
    url: Optional[str] = None
    name: Optional[str] = None


def complete_map_slugs(incomplete: str):
    return (
        db.run_query(
            "SELECT slug FROM maps.sources WHERE slug ILIKE :incomplete",
            {"incomplete": f"{incomplete}%"},
        )
        .scalars()
        .all()
    )


def map_info_parser(identifier: str | int) -> _MapInfo:
    if identifier == "-" or identifier == "active":
        identifier = app.state.get("active_map")
        if identifier is None:
            raise MacrostratError("No active map set")
    return get_map_info(db, identifier)


MapInfo = Annotated[
    _MapInfo,
    Argument(..., autocompletion=complete_map_slugs, parser=map_info_parser),
]


def get_map_info(db: Database, identifier: str | int) -> MapInfo:
    """Get map info for a map ID or slug."""
    query = "SELECT source_id, slug, name, url FROM maps.sources"
    params = {}
    try:
        map_id = int(identifier)
        query += " WHERE source_id = %(source_id)s"
        params["source_id"] = map_id
    except ValueError:
        map_slug = identifier
        query += " WHERE slug = %(slug)s"
        params["slug"] = map_slug

    res = db.run_query(query, params).one()

    return MapInfo(id=res.source_id, slug=res.slug, url=res.url, name=res.name)


def create_sources_record(db, slug) -> MapInfo:
    """
    Create sources record for an existing set of database tables
    """
    params = {
        "primary_table": f"{slug}_polygons",
        "primary_line_table": f"{slug}_lines",
        # Doesn't exist yet, but in prep
        "primary_point_table": f"{slug}_points",
    }
    has_a_table = False
    for k, v in params.items():
        if table_exists(db, v, schema="sources"):
            has_a_table = True
        else:
            params[k] = None

    if not has_a_table:
        raise ValueError(f"No tables found for {slug}")

    params["slug"] = slug

    """Insert a record into the sources table."""
    source_id = db.run_query(
        """
        INSERT INTO maps.sources (slug, primary_table, primary_line_table)
        VALUES (:slug, :primary_table, :primary_line_table)
        ON CONFLICT (slug) DO NOTHING
        RETURNING source_id
        """,
        params,
    ).scalar()
    db.session.commit()

    return MapInfo(id=source_id, slug=slug)


def feature_counts(db, info: MapInfo):
    res = db.run_query(
        """SELECT
            (SELECT count(*) FROM {poly_table} WHERE source_id = :source_id) AS n_polygons,
            (SELECT count(*) FROM {line_table} WHERE source_id = :source_id) AS n_lines,
            (SELECT count(*) FROM {point_table} WHERE source_id = :source_id) AS n_points
        """,
        dict(
            poly_table=Identifier("maps", "polygons"),
            line_table=Identifier("maps", "lines"),
            point_table=Identifier("maps", "points"),
            source_id=info.id,
        ),
    ).one()
    return res
