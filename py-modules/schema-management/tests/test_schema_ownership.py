"""Ownership test for the create-as-owner build.

After a full declarative build (each application chunk applied under ``SET ROLE
macrostrat``), every object in the application schemas must be owned by
``macrostrat`` — proving create-as-owner works without any ``ALTER … OWNER TO``
boilerplate in the SQL. The foundational ``public`` schema is deliberately excluded
(it is applied as the connector/superuser and its ownership stays explicit).

Also asserts the one intentional exception: ``xdd_writer`` keeps write access to
``macrostrat_kg`` (previously implicit via ownership, now via explicit grants).

The structural drift test can't catch an ownership regression — both its sides go
through the same ``build_schema`` — so this is the dedicated check.
"""

import importlib.util

from pytest import fixture, mark

from macrostrat.core.config import settings
from macrostrat.map_topology.config import config as _topo_config
from macrostrat.schema_management.composer import build_schema
from macrostrat.schema_management.defs import temporary_database_cluster
from macrostrat.schema_management.migrations import ApplicationStatus


def _load_ownership_migration():
    """Import the ownership-unification migration from schema/_migrations by path."""
    path = (
        settings.srcroot
        / "schema"
        / "_migrations"
        / "ownership_unification"
        / "__init__.py"
    )
    spec = importlib.util.spec_from_file_location("ownership_unification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.OwnershipUnificationMigration()


_ENV = "development"

# Schemas whose ownership is *not* create-as-owner and is excluded from the check:
# system catalogs, the foundational/shared ``public`` and PostGIS ``topology``, and
# external data schemas the diff never manages.
#
# The map-topology schemas are excluded for a different reason: that chunk is
# function-backed and the topology manager opens its *own* connection
# (``create_context`` builds a fresh ``Database`` from the engine URL), so the
# composer's session-level ``SET ROLE`` doesn't reach it and its objects are born
# owned by the connector. Making them macrostrat-owned would additionally require
# granting ``macrostrat`` write access to the PostGIS ``topology`` metadata tables.
_TOPOLOGY_SCHEMAS = (_topo_config["data_schema"], _topo_config["topo_schema"])

_EXCLUDED_SCHEMAS = (
    "pg_catalog",
    "information_schema",
    "public",
    "topology",
    "sources",
    "tiger",
    "tiger_data",
    *_TOPOLOGY_SCHEMAS,
)

@fixture(scope="module")
def built_schema():
    """One unoptimized build, shared by this module.

    Can't use ``schema_harness``: its ``optimize`` transform skips GRANT and
    ALTER … OWNER TO, which is exactly what these tests inspect.
    """
    with temporary_database_cluster(username="macrostrat_admin") as db:
        build_schema(db, _ENV)
        yield db


@fixture
def rollback_schema(built_schema):
    """``built_schema`` in a transaction rolled back after the test.

    Ownership DDL is transactional, so a test that reassigns owners can share the
    build without leaking into the read-only checks.
    """
    with built_schema.transaction(rollback=True):
        yield built_schema


_OWNERSHIP_QUERY = """
SELECT n.nspname AS schema, c.relname AS name,
       pg_catalog.pg_get_userbyid(c.relowner) AS owner
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')  -- tables, views, matviews, sequences, foreign tables
  AND n.nspname <> ALL(:excluded)
  AND n.nspname NOT LIKE 'pg\\_%'
ORDER BY 1, 2
"""

_SCHEMA_OWNER_QUERY = """
SELECT n.nspname AS schema, pg_catalog.pg_get_userbyid(n.nspowner) AS owner
FROM pg_catalog.pg_namespace n
WHERE n.nspname <> ALL(:excluded)
  AND n.nspname NOT LIKE 'pg\\_%'
ORDER BY 1
"""


@mark.docker
@mark.slow
def test_application_objects_are_macrostrat_owned(built_schema):
    db = built_schema
    params = {"excluded": list(_EXCLUDED_SCHEMAS)}

    bad_objects = [
        (row.schema, row.name, row.owner)
        for row in db.run_query(_OWNERSHIP_QUERY, params)
        if row.owner != "macrostrat"
    ]
    assert not bad_objects, (
        f"non-macrostrat-owned application objects: {bad_objects}"
    )

    bad_schemas = [
        (row.schema, row.owner)
        for row in db.run_query(_SCHEMA_OWNER_QUERY, params)
        if row.owner != "macrostrat"
    ]
    assert not bad_schemas, (
        f"non-macrostrat-owned application schemas: {bad_schemas}"
    )


@mark.docker
@mark.slow
def test_xdd_writer_retains_write_access(built_schema):
    """Ownership collapsed to macrostrat, but xdd_writer keeps write access via grants."""
    db = built_schema
    # A representative macrostrat_kg table the writer must still be able to write.
    privs = db.run_query(
        """
        SELECT
          pg_catalog.has_schema_privilege('xdd_writer', 'macrostrat_kg', 'USAGE') AS schema_usage,
          pg_catalog.has_table_privilege('xdd_writer', 'macrostrat_kg.entity', 'INSERT') AS ins,
          pg_catalog.has_table_privilege('xdd_writer', 'macrostrat_kg.entity', 'UPDATE') AS upd,
          pg_catalog.has_table_privilege('xdd_writer', 'macrostrat_kg.entity', 'DELETE') AS dlt
        """
    ).one()
    assert privs.schema_usage, "xdd_writer lost USAGE on macrostrat_kg"
    assert privs.ins and privs.upd and privs.dlt, (
        f"xdd_writer lost write access on macrostrat_kg.entity: {privs}"
    )


def _owner_of(db, schema, name):
    return db.run_query(
        """
        SELECT pg_catalog.pg_get_userbyid(c.relowner) AS owner
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = :schema AND c.relname = :name
        """,
        dict(schema=schema, name=name),
    ).scalar()


@mark.docker
@mark.slow
def test_ownership_migration_reconciles_legacy_owners(rollback_schema):
    """On an existing DB with legacy ownership, the migration converges it to macrostrat.

    Simulates the pre-unification state (objects owned by macrostrat_admin / xdd_writer),
    then checks the migration gates on it, reconciles ownership, and restores xdd_writer's
    write access — the existing-database counterpart to create-as-owner on fresh builds.
    """
    db = rollback_schema
    # Simulate a legacy database: hand objects back to the pre-unification owners.
    db.run_sql("ALTER TABLE maps.sources OWNER TO macrostrat_admin;")
    db.run_sql("ALTER TABLE macrostrat_kg.entity OWNER TO xdd_writer;")
    assert _owner_of(db, "maps", "sources") == "macrostrat_admin"
    assert _owner_of(db, "macrostrat_kg", "entity") == "xdd_writer"

    migration = _load_ownership_migration()
    assert migration.should_apply(db) == ApplicationStatus.CAN_APPLY

    migration.apply(db)

    # Ownership converged, migration now a no-op, and xdd_writer still writable.
    assert migration.should_apply(db) == ApplicationStatus.APPLIED
    assert _owner_of(db, "maps", "sources") == "macrostrat"
    assert _owner_of(db, "macrostrat_kg", "entity") == "macrostrat"

    can_write = db.run_query(
        "SELECT has_table_privilege('xdd_writer', 'macrostrat_kg.entity', 'INSERT') AS w"
    ).scalar()
    assert can_write, "xdd_writer lost write access after ownership reconciliation"
