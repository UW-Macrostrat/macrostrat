"""Take every write away from `web_anon` and `web_user`.

Anyone with an ORCID iD can sign in and become `web_user`, so that tier (and
the anonymous one beneath it) must confer no write of record. Edits belong to
`web_admin`; a user's own saved locations are the one exception, and those are
guarded by ownership, not by role. See `Feature areas/Authentication and
authorization.md` in the workbench.
"""

from macrostrat.database import Database
from macrostrat.schema_management import Migration

# (relation, privileges) that `web_anon` / `web_user` held and should not. All
# are development-layer objects except the ingestion queue, which the
# `auth-authorized-role` migration also covers.
_WRITE_GRANTS = [
    ("ecosystem.people", "INSERT, UPDATE, DELETE"),
    ("ecosystem.people_roles", "INSERT, UPDATE, DELETE"),
    ("macrostrat_api.people", "INSERT, UPDATE, DELETE"),
    ("macrostrat_api.people_roles", "INSERT, UPDATE, DELETE"),
    ("macrostrat_kg.extraction_feedback", "INSERT, UPDATE, DELETE"),
    ("macrostrat_kg.extraction_feedback_type", "INSERT, UPDATE, DELETE"),
    ("macrostrat_kg.lookup_extraction_type", "INSERT, UPDATE, DELETE"),
    ("macrostrat_api.extraction_feedback", "INSERT, UPDATE, DELETE"),
    ("macrostrat_api.extraction_feedback_type", "INSERT, UPDATE, DELETE"),
    ("macrostrat_api.lookup_extraction_type", "INSERT, UPDATE, DELETE"),
    ("maps_metadata.ingest_process", "UPDATE"),
    ("macrostrat_api.map_ingest", "UPDATE"),
    ("macrostrat_api.map_ingest_tags", "UPDATE"),
    ("macrostrat_api.maps_sources", "UPDATE"),
]

# Functions that rewrite the column tree; EXECUTE on a function is PUBLIC by
# default, so PUBLIC has to be named in the revoke.
_FUNCTIONS = [
    "macrostrat_api.combine_sections(integer[])",
    "macrostrat_api.split_section(integer[])",
]

# Row ownership, for the two per-user tables. The old policies compared the
# role to 'web_user' literally, which would lock an authorized user out of
# their own rows.
_OWNED = "user_id = user_features.current_app_user_id() OR user_features.current_app_role() = 'web_admin'"


def _relation_exists(db: Database, name: str) -> bool:
    return (
        db.run_query("SELECT to_regclass(:name) IS NOT NULL", {"name": name}).scalar()
        is True
    )


def _function_exists(db: Database, signature: str) -> bool:
    return (
        db.run_query(
            "SELECT to_regprocedure(:sig) IS NOT NULL", {"sig": signature}
        ).scalar()
        is True
    )


def _nothing_writable_by_lower_tiers(db: Database) -> bool:
    """True once no listed relation grants a write to web_anon or web_user,
    counting only the relations this database has."""
    for relation, privileges in _WRITE_GRANTS:
        if not _relation_exists(db, relation):
            continue
        for privilege in privileges.split(", "):
            for role in ("web_anon", "web_user"):
                held = db.run_query(
                    "SELECT has_table_privilege(:role, :relation, :privilege)",
                    {"role": role, "relation": relation, "privilege": privilege},
                ).scalar()
                if held:
                    return False
    for signature in _FUNCTIONS:
        if _function_exists(db, signature):
            held = db.run_query(
                "SELECT has_function_privilege('web_anon', :sig, 'EXECUTE')",
                {"sig": signature},
            ).scalar()
            if held:
                return False
    return True


def _saved_locations_owned(db: Database) -> bool:
    """True once the saved-location policies test ownership rather than the
    role name, or when the tables are absent (a database without the
    development layer)."""
    if not _relation_exists(db, "user_features.user_locations"):
        return True
    literal = db.run_query(
        """
        SELECT count(*) FROM pg_policies
        WHERE schemaname = 'user_features'
          AND tablename IN ('user_locations', 'location_tags_intersect')
          AND (qual LIKE :needle OR with_check LIKE :needle)
        """,
        {"needle": "%= 'web_user'%"},
    ).scalar()
    rls_on_links = db.run_query(
        "SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('user_features.location_tags_intersect')"
    ).scalar()
    return literal == 0 and bool(rls_on_links)


class WebWriteLockdownMigration(Migration):
    name = "web-write-lockdown"
    subsystem = "macrostrat_auth"
    description = """
    Revoke every INSERT/UPDATE/DELETE that web_anon or web_user held (people
    directory, knowledge-graph feedback, ingestion queue), restrict the
    section-rewriting RPC functions to web_admin, and make the saved-location
    policies ownership-based so every signed-in tier keeps its own rows.
    """

    # Guarded per object, so it applies the same in a database without the
    # development layer (nothing to revoke there) as in one with it.
    preconditions = []
    postconditions = [_nothing_writable_by_lower_tiers, _saved_locations_owned]

    readiness_state = "beta"

    def apply(self, db: Database):
        for relation, privileges in _WRITE_GRANTS:
            if not _relation_exists(db, relation):
                continue
            db.run_sql(f"REVOKE {privileges} ON {relation} FROM web_anon, web_user")
            db.run_sql(f"GRANT {privileges} ON {relation} TO web_admin")

        for signature in _FUNCTIONS:
            if not _function_exists(db, signature):
                continue
            db.run_sql(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC, web_anon")
            db.run_sql(f"GRANT EXECUTE ON FUNCTION {signature} TO web_admin")

        if _relation_exists(db, "user_features.user_locations"):
            self._own_saved_locations(db)

        db.run_sql("NOTIFY pgrst, 'reload schema'")

    def _own_saved_locations(self, db: Database):
        for table, prefix in [
            ("user_locations", "pl_ul"),
            ("location_tags_intersect", "pl_lti"),
        ]:
            rel = f"user_features.{table}"
            for op in ["select", "insert", "update", "delete"]:
                db.run_sql(f"DROP POLICY IF EXISTS {prefix}_{op} ON {rel}")
            db.run_sql(
                f"CREATE POLICY {prefix}_select ON {rel} FOR SELECT TO web_user, web_admin USING ({_OWNED})"
            )
            db.run_sql(
                f"CREATE POLICY {prefix}_insert ON {rel} FOR INSERT TO web_user, web_admin WITH CHECK ({_OWNED})"
            )
            db.run_sql(
                f"CREATE POLICY {prefix}_update ON {rel} FOR UPDATE TO web_user, web_admin USING ({_OWNED}) WITH CHECK ({_OWNED})"
            )
            db.run_sql(
                f"CREATE POLICY {prefix}_delete ON {rel} FOR DELETE TO web_user, web_admin USING ({_OWNED})"
            )
            db.run_sql(f"ALTER TABLE {rel} ENABLE ROW LEVEL SECURITY")

        db.run_sql(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON user_features.location_tags_intersect TO web_user, web_admin"
        )
        # The view must run as the caller for the base table's policies to apply.
        if _relation_exists(db, "macrostrat_api.location_tags_intersect"):
            db.run_sql(
                "ALTER VIEW macrostrat_api.location_tags_intersect SET (security_invoker = true)"
            )
