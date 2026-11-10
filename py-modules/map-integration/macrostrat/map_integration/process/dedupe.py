"""Removing a map's exact duplicate features, staged and published.

A staging table loaded twice holds every feature twice, and `insert` copies both.
Duplicates here are rows equal in every column but their key; features that
share a geometry but differ in an attribute are distinct and left alone.
"""

from dataclasses import dataclass

from psycopg.sql import SQL, Composed, Identifier

from macrostrat.map_utils.slugs import STAGING_KINDS, table_prefix

from ..utils import MapInfo

#: Published tables and their keys; the lowest key of each duplicate set is kept.
PUBLISHED = {"polygons": "map_id", "lines": "line_id", "points": "point_id"}


@dataclass
class FeatureTable:
    schema: str
    name: str
    key: str
    #: Expressions compared to decide that two rows are the same feature.
    columns: Composed

    @property
    def qualified(self) -> str:
        return f"{self.schema}.{self.name}"

    def params(self, source_id: int) -> dict:
        return dict(
            table=Identifier(self.schema, self.name),
            key=Identifier(self.key),
            columns=self.columns,
            source_id=source_id,
        )


@dataclass
class Duplicates:
    table: str
    rows: int
    duplicates: int


_RANKED = """
SELECT {key}, row_number() OVER (PARTITION BY {columns} ORDER BY {key}) AS n
FROM {table} WHERE source_id = :source_id
"""

_COUNT = f"""
SELECT count(*) AS n_rows, count(*) FILTER (WHERE n > 1) AS n_duplicates
FROM ({_RANKED}) ranked
"""

_DELETE = f"""
DELETE FROM {{table}} WHERE {{key}} IN (
  SELECT {{key}} FROM ({_RANKED}) ranked WHERE n > 1
)
"""


def feature_tables(
    db, map: MapInfo, *, staging_prefix: str = None
) -> list[FeatureTable]:
    """The published and staging tables that hold *map*'s features."""
    prefix = staging_prefix or table_prefix(map.slug)
    tables = [("maps", kind, key) for kind, key in PUBLISHED.items()]
    # A staging table without `_pkid` predates it; `ctid` stands in for the key
    tables += [("sources", f"{prefix}_{kind}", "_pkid") for kind in STAGING_KINDS]

    found = []
    for schema, name, key in tables:
        columns = _columns(db, schema, name)
        if not columns:
            continue
        if key not in columns:
            key = "ctid"
        found.append(FeatureTable(schema, name, key, _compared(columns, key)))
    return found


def count_duplicates(
    db, map: MapInfo, *, staging_prefix: str = None
) -> list[Duplicates]:
    """Count rows and exact duplicates of *map* in each of its feature tables."""
    counts = []
    for t in feature_tables(db, map, staging_prefix=staging_prefix):
        res = db.run_query(_COUNT, t.params(map.id)).one()
        counts.append(Duplicates(t.qualified, res.n_rows, res.n_duplicates))
    return counts


def remove_duplicates(db, map: MapInfo, *, staging_prefix: str = None) -> dict:
    """Delete all but the first of each set of *map*'s identical features.

    One transaction per map. Rows keyed to a deleted polygon or line (legend
    links, lookup, matches) go with it by cascade; the kept copy has its own.
    Returns the rows deleted per table.
    """
    deleted = {}
    with db.transaction():
        for t in feature_tables(db, map, staging_prefix=staging_prefix):
            res = db.run_query(_DELETE, t.params(map.id))
            deleted[t.qualified] = res.rowcount
    return deleted


def _columns(db, schema: str, name: str) -> dict[str, bool]:
    """Column names of a table, each mapped to whether it is a geometry."""
    rows = db.run_query(
        """
        SELECT column_name, udt_name = 'geometry' AS is_geom
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :name
        ORDER BY ordinal_position
        """,
        dict(schema=schema, name=name),
    )
    return {r.column_name: r.is_geom for r in rows}


def _compared(columns: dict[str, bool], key: str) -> Composed:
    # Geometry has no exact equality usable for grouping; its bytes do
    exprs = [
        SQL("md5(ST_AsEWKB({}))").format(Identifier(c)) if is_geom else Identifier(c)
        for c, is_geom in columns.items()
        if c != key
    ]
    return SQL(", ").join(exprs)
