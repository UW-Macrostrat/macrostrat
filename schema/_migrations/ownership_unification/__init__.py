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
alone: the ``public`` and PostGIS ``topology`` schemas, extensions, external data
(``sources``/``tiger``), the ``temp`` scratch schema and ``text_vectors`` stay as
they are — see ``_EXCLUDED`` for why each is out of scope. (This is why a blunt
``REASSIGN OWNED BY macrostrat_admin`` is *not* used — it would also drag those
foundational objects to ``macrostrat``.)

Each object is re-owned in its own short transaction, under a ``lock_timeout``.
``ALTER … OWNER TO`` takes an ``ACCESS EXCLUSIVE`` lock, and one transaction over
every object held each lock until the end: it queued behind any session left idle in
a transaction, and every ordinary query on an object it had already reached queued
behind it. Objects still locked after the retries are reported and left for the next
run.

After re-owning, ``xdd_writer``'s write access — previously implicit via ownership — is
restored with explicit grants matching the declarative schema.

``readiness_state`` is ``ga``, so this reconciles staging and production as well as
dev. It has to: with the legacy roles swept in both spellings, every environment has
objects to converge, and the paths that used to create them connector-owned now apply
their DDL as ``macrostrat`` — leaving this as the one step that fixes what is already
there. Requires the executing role to be superuser or a member of the legacy roles and
``macrostrat`` (true for every deployed connector).
"""

from time import sleep

from sqlalchemy.exc import DBAPIError

from macrostrat.database import Database
from macrostrat.schema_management.migrations import ApplicationStatus, Migration

# Roles whose ownership is collapsed into `macrostrat`. Each appears twice: the
# PG Operator only creates hyphenated roles, so every legacy role has an
# underscored twin that inherits from it. Membership makes the two interchangeable
# for *access*, but not for ownership — an object has exactly one owner — so both
# spellings are swept. `macrostrat_admin` is also the connector role locally, which
# is why anything created outside `build_schema`'s `SET ROLE` lands here.
LEGACY_OWNERS = (
    "macrostrat_admin",
    "macrostrat-admin",
    "xdd_writer",
    "xdd-writer",
)

# Schemas that are NOT create-as-owner and must be left untouched: system catalogs,
# the shared public/topology schemas, and external data. Everything else is an
# application schema. Kept identical to the exclusion set in test_schema_ownership.
#
# `temp` is scratch space created ad hoc by `macrostrat db load-csv` / `load-geo`
# under whatever role ran them; it holds no declared objects, so sweeping it would
# report drift forever. `text_vectors` is the one schema deliberately owned by a
# legacy role — the xdd subsystem grants it to `xdd-writer` outright (see
# `cli/subsystems/xdd`) — so unifying it would revoke that by design.
# `macrostratbak2` is the dead MariaDB-migration copy (see `_definitions/audit`):
# nothing declares it and nothing reads it, so re-owning its ~140 objects is churn.
_EXCLUDED = (
    "pg_catalog",
    "information_schema",
    "public",
    "topology",
    "sources",
    "tiger",
    "tiger_data",
    "temp",
    "text_vectors",
    "macrostratbak2",
)

_APP_SCHEMA = "n.nspname <> ALL(:excluded) AND n.nspname NOT LIKE 'pg\\_%'"

# True while any application-schema object is still owned by a legacy role — the
# postcondition mirror of what `_REASSIGNMENTS` fixes (relations, routines,
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

# One `ALTER … OWNER TO macrostrat` per object still held by a legacy role, schemas
# last. Sequences owned by a table column (serial/identity) are left out: their owner
# is tied to the table and follows it.
_REASSIGNMENTS = f"""
SELECT statement FROM (
  SELECT 1 AS stage, 'ALTER '
      || (CASE c.relkind WHEN 'f' THEN 'FOREIGN TABLE'
                         WHEN 'm' THEN 'MATERIALIZED VIEW'
                         ELSE 'TABLE' END)
      || ' ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
      || ' OWNER TO macrostrat' AS statement
  FROM pg_catalog.pg_class c
  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relkind IN ('r','p','v','m','S','f') AND {_APP_SCHEMA}
    AND pg_catalog.pg_get_userbyid(c.relowner) = ANY(:legacy)
    AND NOT (c.relkind = 'S' AND EXISTS (
      SELECT 1 FROM pg_catalog.pg_depend d
      WHERE d.objid = c.oid AND d.deptype IN ('a','i') AND d.refobjsubid <> 0))
  UNION ALL
  SELECT 2, 'ALTER ' || (CASE WHEN p.prokind = 'a' THEN 'AGGREGATE' ELSE 'ROUTINE' END)
      || ' ' || cast(cast(p.oid AS regprocedure) AS text) || ' OWNER TO macrostrat'
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
  WHERE {_APP_SCHEMA} AND pg_catalog.pg_get_userbyid(p.proowner) = ANY(:legacy)
  UNION ALL
  SELECT 3, 'ALTER TYPE ' || quote_ident(n.nspname) || '.' || quote_ident(t.typname)
      || ' OWNER TO macrostrat'
  FROM pg_catalog.pg_type t
  JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
  WHERE {_APP_SCHEMA} AND pg_catalog.pg_get_userbyid(t.typowner) = ANY(:legacy)
    AND (t.typtype IN ('e','d')
         OR (t.typtype = 'c'
             AND EXISTS (SELECT 1 FROM pg_catalog.pg_class rc
                         WHERE rc.oid = t.typrelid AND rc.relkind = 'c')))
  UNION ALL
  SELECT 4, 'ALTER SCHEMA ' || quote_ident(n.nspname) || ' OWNER TO macrostrat'
  FROM pg_catalog.pg_namespace n
  WHERE {_APP_SCHEMA} AND pg_catalog.pg_get_userbyid(n.nspowner) = ANY(:legacy)
) s
ORDER BY stage, statement
"""

#: How long one `ALTER … OWNER TO` waits for its lock before it is set aside, and
#: how many passes are made over what was set aside.
LOCK_TIMEOUT = "5s"
ATTEMPTS = 3
RETRY_PAUSE = 10

# Restores xdd_writer's write access after its tables are re-owned to macrostrat.
# Mirrors the declarative grants in schema/development/0005-macrostrat_kg.sql, so a
# reconciled DB matches a fresh build. Guarded on the schema existing (dev/local only).
_XDD_GRANTS = """
GRANT USAGE, CREATE ON SCHEMA macrostrat_kg TO xdd_writer;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA macrostrat_kg TO xdd_writer;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA macrostrat_kg TO xdd_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_kg
  GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO xdd_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_kg
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO xdd_writer;
"""


class OwnershipUnificationMigration(Migration):
    name = "ownership-unification"
    subsystem = "core"
    readiness_state = "ga"
    load_sql_files = False

    def should_apply(self, db: Database) -> ApplicationStatus:
        needs = db.run_query(
            _NEEDS_RECONCILIATION,
            dict(legacy=list(LEGACY_OWNERS), excluded=list(_EXCLUDED)),
        ).scalar()
        return ApplicationStatus.CAN_APPLY if needs else ApplicationStatus.APPLIED

    def apply(self, db: Database):
        pending = [
            r.statement
            for r in db.run_query(
                _REASSIGNMENTS,
                dict(legacy=list(LEGACY_OWNERS), excluded=list(_EXCLUDED)),
            )
        ]
        db.session.commit()
        print(f"Re-owning {len(pending)} objects")

        for attempt in range(ATTEMPTS):
            if attempt > 0:
                print(f"{len(pending)} objects locked; retrying in {RETRY_PAUSE} s")
                sleep(RETRY_PAUSE)
            pending = [stmt for stmt in pending if not _reassign(db, stmt)]
            if not pending:
                break

        if pending:
            print(
                f"{len(pending)} objects stayed locked and keep their owner until the"
                " next run. A session idle in a transaction is the usual holder:"
            )
            for stmt in pending:
                print(f"  {stmt}")

        # Re-owning macrostrat_kg's tables away from xdd_writer stripped its
        # (ownership-implicit) write access; restore it explicitly. Dev/local only.
        has_xdd = db.run_query(
            "SELECT to_regnamespace('macrostrat_kg') IS NOT NULL AS present"
        ).scalar()
        if has_xdd:
            db.run_sql(_XDD_GRANTS)


def _reassign(db: Database, statement: str) -> bool:
    """Re-own one object in its own short transaction. False if its lock was not
    granted within `LOCK_TIMEOUT`.

    The statement runs in a savepoint, so a timeout undoes only this object -- which
    also keeps it safe inside a caller's transaction, such as a test's rollback."""
    try:
        with db.session.begin_nested():
            conn = db.session.connection()
            conn.exec_driver_sql(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'")
            conn.exec_driver_sql(statement, execution_options={"no_parameters": True})
    except DBAPIError as err:
        if _sqlstate(err) != "55P03":  # lock_not_available
            raise
        db.session.commit()
        return False
    db.session.commit()
    return True


def _sqlstate(err: DBAPIError):
    # psycopg 3 exposes `sqlstate`, psycopg 2 `pgcode`; both drivers are installed.
    return getattr(err.orig, "sqlstate", None) or getattr(err.orig, "pgcode", None)
