from macrostrat.core.migrations import ApplicationStatus, Migration
from macrostrat.database import Database


class StorageSchemeMigration(Migration):
    name = "storage-scheme"

    depends_on = ["api-v3"]
    readiness_state = "ga"

    def apply(self, db: Database):
        db.run_sql(
            """
        CREATE TYPE storage.scheme AS ENUM ('s3', 'https', 'http');
        ALTER TYPE storage.scheme ADD VALUE 'https' AFTER 's3';
        ALTER TYPE storage.scheme ADD VALUE 'http' AFTER 'https';

        -- Lock the table to prevent concurrent updates
        LOCK TABLE storage.objects  IN ACCESS EXCLUSIVE MODE;

        ALTER TABLE storage.objects 
        ALTER COLUMN scheme
              TYPE storage.scheme USING scheme::text::storage.scheme;

        -- Unlock the table
        COMMIT;

        DROP TYPE IF EXISTS macrostrat.schemeenum;
        """
        )

        db.run_sql("GRANT USAGE ON SCHEMA storage TO macrostrat;")
        db.run_sql(
            "GRANT SELECT, REFERENCES ON ALL TABLES IN SCHEMA storage TO macrostrat;"
        )
        db.run_sql("GRANT USAGE ON ALL SEQUENCES IN SCHEMA storage TO macrostrat;")
        db.run_sql("GRANT USAGE ON ALL TYPES IN SCHEMA storage TO macrostrat;")

    def should_apply(self, db: Database):
        if has_enum(db, "schemeenum", schema="macrostrat"):
            return ApplicationStatus.CAN_APPLY
        else:
            return ApplicationStatus.APPLIED


def has_enum(db: Database, name: str, schema: str = None):
    sql = "select 1 from pg_type where typname = :name"
    if schema is not None:
        sql += (
            " and typnamespace = (select oid from pg_namespace where nspname = :schema)"
        )

    return db.run_query(
        f"select exists ({sql})", dict(name=name, schema=schema)
    ).scalar()
