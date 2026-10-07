"""Add the `authorized` tier between `user` and `admin`.

See `Feature areas/Authentication and authorization.md` in the workbench.
"""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists


def _role_row_exists(role_id: str):
    return lambda db: (
        db.run_query(
            "SELECT count(*) FROM macrostrat_auth.role WHERE id = :id", {"id": role_id}
        ).scalar()
        > 0
    )


def _pg_role_exists(name: str):
    return lambda db: (
        db.run_query(
            "SELECT count(*) FROM pg_roles WHERE rolname = :name", {"name": name}
        ).scalar()
        > 0
    )


class AuthAuthorizedRoleMigration(Migration):
    name = "auth-authorized-role"
    subsystem = "macrostrat_auth"
    # Creating a Postgres role and granting it to the authenticator need more
    # than the application role has; the whole thing is written for the connector.
    owner = None
    description = """
    Add the web_authorized Postgres role (view everything, edit nothing) between
    web_user and web_admin, the `authorized` application role that maps to it,
    and take ingestion-queue writes away from web_user.
    """

    depends_on = ["auth-role-identifiers"]

    preconditions = [exists("macrostrat_auth", "role")]

    postconditions = [
        _pg_role_exists("web_authorized"),
        _role_row_exists("authorized"),
    ]

    readiness_state = "beta"

    def apply(self, db: Database):
        # The role is cluster-wide, so it may already exist from another
        # database's build; a duplicate raises and is stepped over.
        db.run_sql("CREATE ROLE web_authorized NOLOGIN")
        db.run_sql("GRANT web_authorized TO postgrest")
        # Re-nest the tiers: web_admin now reaches web_user through web_authorized.
        db.run_sql("GRANT web_user TO web_authorized")
        db.run_sql("GRANT web_authorized TO web_admin")
        db.run_sql("REVOKE web_user FROM web_admin")

        db.run_sql(
            """
            ALTER TABLE macrostrat_auth.role
                DROP CONSTRAINT role_postgres_role_is_a_web_role,
                ADD CONSTRAINT role_postgres_role_is_a_web_role
                    CHECK (postgres_role IN ('web_user', 'web_authorized', 'web_admin', 'web_anon'))
            """
        )
        db.run_sql(
            """
            INSERT INTO macrostrat_auth.role (id, postgres_role, description) VALUES
                ('authorized', 'web_authorized', 'A user designated by an administrator to view everything')
            ON CONFLICT (id) DO UPDATE
                SET postgres_role = EXCLUDED.postgres_role,
                    description   = EXCLUDED.description
            """
        )

        # A signed-in user is anyone with an ORCID iD; the ingestion queue is
        # written by administrators only. Matches the declarative grants in
        # schema/core/0003-maps-metadata.
        for relation in [
            "maps_metadata.ingest_process",
            "macrostrat_api.map_ingest",
            "macrostrat_api.map_ingest_tags",
            "macrostrat_api.maps_sources",
        ]:
            db.run_sql(f"REVOKE UPDATE ON {relation} FROM web_user")
            db.run_sql(f"GRANT UPDATE ON {relation} TO web_admin")

        db.run_sql("NOTIFY pgrst, 'reload schema'")
