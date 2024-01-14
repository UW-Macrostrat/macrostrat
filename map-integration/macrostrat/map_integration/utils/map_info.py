from pathlib import Path
from typing import Optional

from macrostrat.database import Database
from pydantic import BaseModel


class MapInfo(BaseModel):
    """Basic information about a map."""

    id: int
    slug: str
    url: Optional[str] = None
    name: Optional[str] = None


def get_map_info(db: Database, identifier: str | int) -> MapInfo:
    """Get map info for a map ID or slug."""
    query = "SELECT source_id, slug, name, url FROM maps.sources"
    params = {}
    try:
        map_id = int(identifier)
        query += " WHERE id = %(source_id)s"
        params["source_id"] = map_id
    except ValueError:
        map_slug = identifier
        query += " WHERE slug = %(slug)s"
        params["slug"] = map_slug

    res = db.run_query(query, params).one()

    return MapInfo(id=res.source_id, slug=res.slug, url=res.url, name=res.name)
