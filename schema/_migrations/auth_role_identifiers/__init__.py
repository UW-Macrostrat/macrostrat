"""Carry a database over to the string-keyed `macrostrat_auth.role`.

See `Feature areas/Authentication and authorization.md` in the workbench.
"""

from macrostrat.schema_management import Migration, column_type_is, exists, has_columns


class AuthRoleIdentifiersMigration(Migration):
    name = "auth-role-identifiers"
    subsystem = "macrostrat_auth"
    description = """
    Key macrostrat_auth.role on the role's own name, add its postgres_role
    mapping, and replace macrostrat_auth."user".role_id with a text `role`
    foreign key.
    """

    # Only a database still on the integer-keyed shape; inert on a fresh build.
    preconditions = [
        exists("macrostrat_auth", "role", "user"),
        column_type_is("macrostrat_auth", "role", "id", "integer"),
    ]

    # The retyped key and the new FK column: states the old shape cannot reach,
    # so this reads as APPLIED only once it has actually run.
    postconditions = [
        column_type_is("macrostrat_auth", "role", "id", "text"),
        has_columns("macrostrat_auth", "role", "postgres_role"),
        has_columns("macrostrat_auth", "user", "role"),
    ]

    # Rehearsed in development; not yet against a production-shaped clone.
    readiness_state = "beta"
