"""Mocked (no-database) tests for the schema composer.

These use a fake ``Database`` that just records which fixture paths would be
applied, so chunk ordering and target-closure selection can be verified quickly
without Docker. This complements the docker-backed parity/harness tests.
"""

from pathlib import Path

from pytest import raises

from macrostrat.schema_management.chunks import chunks_for_environment
from macrostrat.schema_management.composer import build_schema, dependency_closure

# Topology is local-only, so "development" is a full-but-topology-free build with
# only Path providers (no callables to execute against the fake DB).
_ENV = "development"


class FakeDB:
    """Records applied fixture paths instead of touching a database."""

    def __init__(self):
        self.applied: list[Path] = []

    def run_fixtures(self, fixtures, **kwargs):
        self.applied.extend(fixtures)


def _names(db: FakeDB) -> list[str]:
    return [p.name for p in db.applied]


def test_target_closure_builds_only_subsystem_and_deps():
    db = FakeDB()
    build_schema(db, _ENV, target="macrostrat")
    names = _names(db)

    # public + macrostrat are built...
    assert "0001-public.sql" in names
    assert "01-main.sql" in names  # 0002-macrostrat/01-main.sql
    # ...but nothing from the `core` remainder or the dev layer.
    assert "0002-storage.sql" not in names
    assert "0002-macrostrat_auth.sql" not in names


def test_full_build_applies_all_core_and_dev():
    db = FakeDB()
    build_schema(db, _ENV)
    names = _names(db)

    assert "0002-storage.sql" in names
    assert "0047-tile_layers.fossils.sql" in names


def test_application_order_follows_dependency_chain():
    db = FakeDB()
    build_schema(db, _ENV)
    names = _names(db)

    # public -> macrostrat -> core remainder
    assert names.index("0001-public.sql") < names.index("01-main.sql")
    assert names.index("01-main.sql") < names.index("0002-storage.sql")


def test_dependency_closure_of_macrostrat():
    chunks = chunks_for_environment(_ENV)
    assert dependency_closure(chunks, "macrostrat") == {"public", "macrostrat"}


def test_dependency_closure_unknown_target_raises():
    chunks = chunks_for_environment(_ENV)
    with raises(ValueError):
        dependency_closure(chunks, "does-not-exist")
