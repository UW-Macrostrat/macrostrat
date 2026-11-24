"""Importing the pre-switchover tileserver lineage from a legacy stats database.

The legacy tables stand in a `stats` schema of the shared test database, which
the import reads through its own session, as it would a separate database.
"""

from pytest import fixture, raises

from macrostrat.database import Database
from macrostrat.usage_stats.legacy import import_legacy_lineage, legacy_schema

LEGACY_TABLES = """
CREATE SCHEMA stats;
CREATE TABLE stats.day_index (
  layer text NOT NULL, ext text NOT NULL, referrer text NOT NULL,
  app text NOT NULL, app_version text NOT NULL, date timestamp NOT NULL,
  num_requests integer NOT NULL
);
CREATE TABLE stats.location_index (
  layer text NOT NULL, ext text NOT NULL, x integer NOT NULL, y integer NOT NULL,
  z integer NOT NULL, orig_z integer NOT NULL, num_requests integer NOT NULL
);
INSERT INTO stats.day_index
SELECT 'carto', 'mvt', 'none', 'none', 'none', d, 10
FROM generate_series('2018-02-07'::timestamp, '2018-03-08', '1 day') d;
INSERT INTO stats.location_index
SELECT 'carto', 'png', x, y, 8, 12, 2
FROM generate_series(0, 9) x, generate_series(0, 9) y;
"""


@fixture(scope="module")
def usage_db(schema_harness):
    return schema_harness.load_schema(target="usage-stats")


@fixture
def source(usage_db):
    usage_db.run_sql(LEGACY_TABLES)
    db = Database(usage_db.engine)
    try:
        yield db
    finally:
        db.session.close()  # releases its locks on the tables dropped below
        usage_db.run_sql("DROP SCHEMA stats CASCADE")


@fixture
def target(usage_db):
    with usage_db.transaction(rollback="always"):
        yield usage_db


def test_imports_and_reconciles(source, target):
    # A log-harvested row on a legacy date belongs to the other lineage.
    target.run_query(
        "INSERT INTO usage_stats.tileserver_day_index "
        "(layer, ext, referrer, app, app_version, date, num_requests, new_system) "
        "VALUES ('carto', 'mvt', 'none', 'none', 'none', '2018-02-07', 99, true)"
    )

    day, location = import_legacy_lineage(source, target, batch_size=7)

    assert (day.source_rows, day.source_requests) == (30, 300)
    assert (location.source_rows, location.source_requests) == (100, 200)
    assert day.inserted == 30 and location.inserted == 100
    assert day.reconciles and location.reconciles
    # The lineage defaults filled the key columns the legacy tables lack.
    assert target.run_query(
        "SELECT DISTINCT is_bot, x_cache, x_tile_cache "
        "FROM usage_stats.tileserver_day_index WHERE NOT new_system"
    ).all() == [(False, "", "")]


def test_rerun_adds_nothing(source, target):
    import_legacy_lineage(source, target)
    again = import_legacy_lineage(source, target)
    assert [r.inserted for r in again] == [0, 0]
    assert all(r.reconciles for r in again)


def test_existing_rows_are_kept_and_flagged(source, target):
    import_legacy_lineage(source, target)
    target.run_query(
        "UPDATE usage_stats.tileserver_day_index SET num_requests = 11 "
        "WHERE NOT new_system AND date = '2018-02-07'"
    )
    day, _ = import_legacy_lineage(source, target)
    assert day.inserted == 0
    assert not day.reconciles


def test_core_database_is_refused(source):
    source.run_query("ALTER TABLE stats.day_index ADD COLUMN new_system boolean")
    with raises(ValueError, match="new_system"):
        legacy_schema(source)
