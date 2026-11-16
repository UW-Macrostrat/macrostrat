"""Mocked (no-database) tests for the schema composer.

Macrostrat's own chunk graph, checked with a fake ``Database`` that records
which fixture paths would be applied. The composer itself is tested in
``macrostrat.schema_management``.
"""

from dataclasses import replace
from pathlib import Path

from sqlalchemy import create_engine

from macrostrat.schema.chunks import chunks_for_environment
from macrostrat.schema_management import SchemaDefinition
from macrostrat.schema_management.composer import build_schema, dependency_closure

_ENV = "development"


def _sql_only_chunks(env: str = _ENV) -> list[SchemaDefinition]:
    """The chunks for ``env`` with callable providers dropped.

    Callable providers (e.g. ``map-topology``) delegate to libraries that open
    their own connection and issue real DDL, so they can't run against a fake
    database. These tests are about *which SQL files* get applied and in what
    order, so the chunks keep their place in the graph with only their Path
    providers.
    """
    return [
        replace(c, provides=[p for p in c.provides if isinstance(p, Path)])
        for c in chunks_for_environment(env)
    ]


class FakeDB:
    """Records applied fixture paths and role changes instead of touching a database."""

    def __init__(self):
        self.applied: list[Path] = []
        # Sequence of role directives issued by build_schema, as raw SQL strings.
        self.roles: list[str] = []
        # Never connects; only carries the pool listeners `pin_role` installs.
        self.engine = create_engine("postgresql+psycopg://")

    def run_fixtures(self, fixtures, **kwargs):
        self.applied.extend(fixtures)

    def run_sql(self, sql, params=None, **kwargs):
        # build_schema only issues SET ROLE / RESET ROLE through this path.
        self.roles.append(sql)


def _names(db: FakeDB) -> list[str]:
    return [p.name for p in db.applied]


def test_full_build_applies_all_core_and_dev():
    db = FakeDB()
    build_schema(db, _sql_only_chunks())
    names = _names(db)

    assert "0002-storage.sql" in names
    assert "0047-tile_layers.fossils.sql" in names


def test_target_closure_builds_only_subsystem_and_deps():
    db = FakeDB()
    build_schema(db, _sql_only_chunks(), target="macrostrat")
    names = _names(db)

    # public + macrostrat are built...
    assert "0001-public.sql" in names
    assert "01-main.sql" in names  # 0002-macrostrat/01-main.sql
    # ...but nothing from the `core` remainder, the `maps` subsystem, or the dev
    # layer (maps depends on macrostrat, not the reverse, so it isn't pulled in).
    assert "0002-storage.sql" not in names  # `core` (after the maps boundary)
    assert "01-maps.sql" not in names  # `maps` subsystem


def test_application_order_follows_dependency_chain():
    db = FakeDB()
    build_schema(db, _sql_only_chunks())
    names = _names(db)

    # public -> macrostrat -> core remainder
    assert names.index("0001-public.sql") < names.index("01-main.sql")
    assert names.index("01-main.sql") < names.index("0002-storage.sql")


def test_dependency_closure_of_macrostrat():
    chunks = chunks_for_environment(_ENV)
    assert dependency_closure(chunks, "macrostrat") == {"public", "macrostrat"}
