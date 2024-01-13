from pathlib import Path
from pydantic import BaseModel
from macrostrat.database import Database


class MapIdentifier(BaseModel):
    """A Macrostrat map identifier."""

    id: int
    slug: str
    url: str = None
    name: str = None


def get_map_identifier(db: Database, identifier: str | int) -> MapIdentifier:
    """Get a map identifier from a map ID or slug."""
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

    res = next(db.run_sql(query, params=params)).first()

    return MapIdentifier(id=res.source_id, slug=res.slug, url=res.url, name=res.name)


def _unlink_if_exists(filename: Path, overwrite: bool = False):
    file_exists = filename.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        filename.unlink()
