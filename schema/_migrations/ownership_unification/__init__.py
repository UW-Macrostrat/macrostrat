"""Reconcile object ownership on *existing* databases to the create-as-owner model.

Fresh builds get single-role ownership for free: each application chunk is applied
under ``SET ROLE macrostrat`` (see ``composer.build_schema``), so objects are born
``macrostrat``-owned. Existing databases can't be fixed the same way — the schema
*diff* (``results.dbdiff``) is ownership-blind (it never emits ``ALTER … OWNER TO``),
so ``plan``/``apply`` can neither detect nor converge ownership. An ownership change
is therefore a non-diffable transition, which is exactly what the Migration system is
for.

Scope: **application schemas only** — the same boundary create-as-owner establishes and
``test_schema_ownership`` asserts. Foundational/shared ownership is deliberately left
alone: the ``public`` and PostGIS ``topology`` schemas, extensions, and external data
(``sources``/``tiger``) stay owned by the superuser/``postgres`` as before. (This is why
a blunt ``REASSIGN OWNED BY macrostrat_admin`` is *not* used — it would also drag those
foundational objects to ``macrostrat``.) The actual re-owning is in
``reassign_ownership.sql`` (run as a fixture so its ``format()`` placeholders survive).

After re-owning, ``xdd_writer``'s write access — previously implicit via ownership — is
restored with explicit grants matching the declarative schema.

``readiness_state`` is ``alpha`` (dev only): validate against a staging clone, then
promote to ``ga`` to reconcile staging/prod. Requires the executing role to be superuser
or a member of the legacy roles and ``macrostrat`` (true for the dev connector).
"""

from pathlib import Path

from macrostrat.database import Database
from macrostrat.schema_management.migrations import ApplicationStatus, Migration

# Roles whose ownership is collapsed into `macrostrat`.
LEGACY_OWNERS = ("macrostrat_admin", "xdd_writer")

# Schemas that are NOT create-as-owner and must be left untouched: system catalogs,
# the shared public/topology schemas, and external data. Everything else is an
# application schema. Kept identical to the list in reassign_ownership.sql and the
# exclusion set in test_schema_ownership.
_EXCLUDED = (
    "pg_catalog",
    "information_schema",
    "public",
    "topology",
    "sources",
    "tiger",
    "tiger_data",
)

_APP_SCHEMA = "n.nspname <> ALL(:excluded) AND n.nspname NOT LIKE 'pg\\_%'"

# True while any application-schema object is still owned by a legacy role — the
# postcondition mirror of what reassign_ownership.sql fixes (relations, routines,
# standalone types, schemas).
_NEEDS_RECONCILIATION = f"""
SELECT
  EXISTS (
    SELECT 1 FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r','p','v','m','S','f') AND {_APP_SCHEMA}
      AND pg_catalog.pg_get_userbyid(c.relowner) = ANY(:legacy)
  ) OR EXISTS (
    SELECT 1 FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE {_APP_SCHEMA} AND pg_catalog.pg_get_userbyid(p.proowner) = ANY(:legacy)
  ) OR EXISTS (
    SELECT 1 FROM pg_catalog.pg_type t
    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
    WHERE {_APP_SCHEMA} AND pg_catalog.pg_get_userbyid(t.typowner) = ANY(:legacy)
      AND (t.typtype IN ('e','d')
           OR (t.typtype = 'c'
               AND EXISTS (SELECT 1 FROM pg_catalog.pg_class rc
                           WHERE rc.oid = t.typrelid AND rc.relkind = 'c')))
  ) OR EXISTS (
    SELECT 1 FROM pg_catalog.pg_namespace n
    WHERE {_APP_SCHEMA} AND pg_catalog.pg_get_userbyid(n.nspowner) = ANY(:legacy)
  ) AS needs_reconciliation
"""

# Restores xdd_writer's write access after its tables are re-owned to macrostrat.
# Mirrors the declarative grants in schema/development/0005-macrostrat_xdd.sql, so a
# reconciled DB matches a fresh build. Guarded on the schema existing (dev/local only).
_XDD_GRANTS = """
GRANT USAGE, CREATE ON SCHEMA macrostrat_xdd TO xdd_writer;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA macrostrat_xdd TO xdd_writer;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA macrostrat_xdd TO xdd_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_xdd
  GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO xdd_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_xdd
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO xdd_writer;
"""


class OwnershipUnificationMigration(Migration):
    name = "ownership-unification"
    subsystem = "core"
    # Dev-only until validated against a staging clone; promote to reconcile prod.
    readiness_state = "alpha"
    load_sql_files = False

    def should_apply(self, db: Database) -> ApplicationStatus:
        needs = db.run_query(
            _NEEDS_RECONCILIATION,
            dict(legacy=list(LEGACY_OWNERS), excluded=list(_EXCLUDED)),
        ).scalar()
        return ApplicationStatus.CAN_APPLY if needs else ApplicationStatus.APPLIED

    def apply(self, db: Database):
        # Run as a fixture (file) so the SQL's format() `%` placeholders survive.
        db.run_fixtures(Path(__file__).parent / "reassign_ownership.sql")

        # Re-owning macrostrat_xdd's tables away from xdd_writer stripped its
        # (ownership-implicit) write access; restore it explicitly. Dev/local only.
        has_xdd = db.run_query(
            "SELECT to_regnamespace('macrostrat_xdd') IS NOT NULL AS present"
        ).scalar()
        if has_xdd:
            db.run_sql(_XDD_GRANTS)
