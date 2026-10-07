"""The `map-source-kebab-slugs` migration, run on a database put back into the
state it was written for: underscore and irregular slugs, staging tables named
after them, and `ingest_process.slug` still present."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from pytest import fixture, raises

from macrostrat.core.exc import MacrostratError
from macrostrat.schema_management import ApplicationStatus

MIGRATION = (
    Path(__file__).parents[3] / "schema/_migrations/map_source_kebab_slugs/__init__.py"
)

LEGACY = """
ALTER TABLE maps.sources DROP CONSTRAINT sources_slug_kebab;
ALTER TABLE maps_metadata.ingest_process ADD COLUMN slug text REFERENCES maps.sources (slug);
INSERT INTO maps.sources (slug, primary_table, primary_line_table, scale) VALUES
  ('legacy_map', 'legacy_map_polygons', 'legacy_map_lines', 'large'),
  ('odd-_name x', 'odd-_name x_polygons', NULL, 'large');
CREATE TABLE sources.legacy_map_polygons (id integer);
CREATE TABLE sources.legacy_map_lines (id integer);
CREATE TABLE sources."odd-_name x_polygons" (id integer);
INSERT INTO maps_metadata.ingest_process (source_id, slug)
SELECT source_id, slug FROM maps.sources WHERE slug = 'legacy_map';
"""

CLEANUP = """
DELETE FROM maps_metadata.ingest_process
WHERE source_id IN (SELECT source_id FROM maps.sources WHERE slug ~ '^(legacy|odd|dup)');
DELETE FROM maps.sources WHERE slug ~ '^(legacy|odd|dup)';
DROP TABLE IF EXISTS sources.legacy_map_polygons, sources.legacy_map_lines,
  sources."odd-_name x_polygons", sources.odd_name_x_polygons;
"""


def _module():
    spec = spec_from_file_location("map_source_kebab_slugs", MIGRATION)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _migration():
    return _module().MapSourceKebabSlugsMigration()


def _scalar(db, sql, **params):
    return db.run_query(sql, params).scalar()


@fixture
def legacy_db(test_db_base):
    db = test_db_base
    db.run_sql(LEGACY, raise_errors=True)
    try:
        yield db
    finally:
        # The migration commits, so the declarative state is put back by hand.
        db.session.rollback()
        db.run_sql(CLEANUP, raise_errors=True)
        db.run_sql(
            "ALTER TABLE maps_metadata.ingest_process DROP COLUMN IF EXISTS slug",
            raise_errors=True,
        )
        module = _module()
        if not module._has_constraint(db):
            db.run_sql(
                f"ALTER TABLE maps.sources ADD CONSTRAINT {module.CONSTRAINT}"
                f" CHECK (slug ~ '{module.SLUG_PATTERN}')",
                raise_errors=True,
            )


def test_refuses_collisions(legacy_db):
    db = legacy_db
    db.run_sql(
        "INSERT INTO maps.sources (slug, scale) VALUES ('dup_a', 'large'), ('dup-a', 'large')",
        raise_errors=True,
    )
    migration = _migration()
    with raises(MacrostratError) as err:
        migration.apply(db)
    ids = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug IN ('dup_a', 'dup-a') ORDER BY 1"
    ).scalars()
    # Each colliding map is named by source id, so it can be targeted
    assert all(f"({i})" in err.value.details for i in ids)
    # Refused before anything was written
    assert (
        _scalar(db, "SELECT count(*) FROM maps.sources WHERE slug = 'legacy_map'") == 1
    )
    db.run_sql("DELETE FROM maps.sources WHERE slug ~ '^dup'", raise_errors=True)


def test_rewrites_slugs_and_tables(legacy_db):
    db = legacy_db
    migration = _migration()
    assert migration.should_apply(db) == ApplicationStatus.CAN_APPLY

    migration.apply(db)

    rows = dict(
        db.run_query(
            "SELECT slug, primary_table FROM maps.sources"
            " WHERE slug IN ('legacy-map', 'odd-name-x')"
        ).all()
    )
    # Underscore slugs keep their tables; an irregular one's tables follow it
    assert rows == {
        "legacy-map": "legacy_map_polygons",
        "odd-name-x": "odd_name_x_polygons",
    }
    assert _scalar(db, "SELECT to_regclass('sources.odd_name_x_polygons') IS NOT NULL")
    assert _scalar(db, "SELECT to_regclass('sources.legacy_map_lines') IS NOT NULL")
    assert (
        _scalar(
            db,
            "SELECT count(*) FROM maps_metadata.ingest_process p"
            " JOIN maps.sources s USING (source_id) WHERE s.slug = 'legacy-map'",
        )
        == 1
    )
    assert _scalar(db, "SELECT to_regclass('macrostrat_api.map_ingest') IS NOT NULL")
    # As the migration runner does before checking postconditions
    db.refresh_schema()
    assert migration.should_apply(db) == ApplicationStatus.APPLIED

    with raises(Exception):
        db.run_sql(
            "INSERT INTO maps.sources (slug, scale) VALUES ('legacy_again', 'large')",
            raise_errors=True,
        )


def test_underscore_slugs_resolve_before_migrating(legacy_db):
    from macrostrat.map_integration.utils.map_info import get_map_info, resolve_maps

    db = legacy_db
    db.run_sql(
        "INSERT INTO maps.sources (slug, scale) VALUES ('legacy-map', 'large')",
        raise_errors=True,
    )
    # The name as typed wins; its hyphenated form is a separate map
    assert get_map_info(db, "legacy_map").slug == "legacy_map"
    assert get_map_info(db, "legacy-map").slug == "legacy-map"
    assert get_map_info(db, "odd-_name x").slug == "odd-_name x"
    assert {m.slug for m in resolve_maps(db, ["legacy_*"])} == {
        "legacy_map",
        "legacy-map",
    }
    exact = _scalar(db, "SELECT map_bounds.source_id('legacy_map')")
    assert exact == _scalar(
        db, "SELECT source_id FROM maps.sources WHERE slug = 'legacy_map'"
    )
