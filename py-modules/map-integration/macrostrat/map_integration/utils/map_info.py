from typing import Optional

from psycopg2.sql import Identifier
from pydantic import BaseModel
from typer import Argument
from typing_extensions import Annotated

from macrostrat.core import app
from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database

from ..database import get_database
from ._database import table_exists


class _MapInfo(BaseModel):
    """Basic information about a map."""

    id: int
    slug: str
    url: Optional[str] = None
    name: Optional[str] = None

    @property
    def source_id(self):
        return self.id


def complete_map_slugs(incomplete: str):
    db = get_database()
    return (
        db.run_query(
            "SELECT slug FROM maps.sources WHERE slug ILIKE :incomplete",
            {"incomplete": f"{incomplete}%"},
        )
        .scalars()
        .all()
    )


def map_info_parser(identifier: str | int) -> _MapInfo:
    db = get_database()
    if identifier == "-" or identifier == "active":
        identifier = app.state.get("active_map")
        if identifier is None:
            raise MacrostratError("No active map set")
    return get_map_info(db, identifier)


MapInfo = Annotated[
    _MapInfo,
    Argument(..., autocompletion=complete_map_slugs, parser=map_info_parser),
]


def _selector_to_like(selector: str) -> str:
    """Translate a shell-style glob into a SQL `LIKE` pattern."""
    return (
        selector.replace("%", r"\%")
        .replace("_", r"\_")
        .replace("*", "%")
        .replace("?", "_")
    )


def resolve_maps(db: Database, selectors: list[str]) -> list[_MapInfo]:
    """Expand map selectors -- source ids, slugs, or slug globs -- to map info.

    `ngs-*` names a compilation's 114 members without listing them, which is the
    same targeting `macrostrat bounds build` accepts. Quote the pattern in a
    shell, which would otherwise try to expand it against filenames.

    Order follows `source_id`, and a map named twice appears once. A selector
    matching nothing raises rather than being skipped quietly -- a typo'd glob
    would otherwise look like a successful run over no maps.
    """
    found: dict[int, _MapInfo] = {}
    for selector in selectors:
        if selector in ("-", "active"):
            active = app.state.get("active_map")
            if active is None:
                raise MacrostratError("No active map set")
            selector = active

        if any(ch in selector for ch in "*?"):
            rows = db.run_query(
                "SELECT source_id, slug, name, url FROM maps.sources"
                " WHERE slug LIKE :pattern ORDER BY source_id",
                dict(pattern=_selector_to_like(selector)),
            ).all()
            if not rows:
                raise MacrostratError(f"No maps match {selector!r}")
            for r in rows:
                found[r.source_id] = MapInfo(
                    id=r.source_id, slug=r.slug, url=r.url, name=r.name
                )
        else:
            info = get_map_info(db, selector)
            found[info.id] = info

    return [found[k] for k in sorted(found)]


MapSelector = Annotated[
    list[str],
    Argument(
        ...,
        autocompletion=complete_map_slugs,
        help="Map slugs, source ids, or slug globs (e.g. 'ngs-*')",
    ),
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

    res = db.run_query(query, params).one_or_none()
    if res is None:
        # `.one()` here raised a bare `NoResultFound` that named neither the
        # identifier nor the fact that a glob had been handed to a command
        # taking a single map -- which is the likeliest way to get here.
        hint = ""
        if any(ch in str(identifier) for ch in "*?"):
            hint = " -- this command takes one map, not a pattern"
        raise MacrostratError(f"No map found matching {identifier!r}{hint}")

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


def feature_counts(db: Database, info: MapInfo):
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


def has_map_schema_data(db: Database, map: MapInfo):
    counts = feature_counts(db, map)
    total = counts.n_polygons + counts.n_lines + counts.n_points
    return total > 0
