"""Standardize `macrostrat_auth.role` on a semantic string key.

`role` was a serial-keyed lookup table and `user.role_id` an integer FK, so
every call site had to join the table back before the value meant anything.
This retypes the key to the role's own name (`user` / `admin` / `test`) and
replaces `user.role_id` with a `user.role` text FK.

The declarative chunk (`schema/core/0002-macrostrat_auth.sql`) already produces
this shape for a fresh build; this migration carries an existing database over.
"""

from macrostrat.schema_management import Migration, column_type_is, exists, has_columns


class AuthRoleIdentifiersMigration(Migration):
    name = "auth-role-identifiers"
    subsystem = "macrostrat_auth"
    description = """
    Retype macrostrat_auth.role.id from serial to the role's name, add its
    postgres_role mapping, and replace macrostrat_auth."user".role_id with a
    text `role` foreign key.
    """

    # Only applicable to a database still on the integer-keyed shape.
    preconditions = [
        exists("macrostrat_auth", "role", "user"),
        column_type_is("macrostrat_auth", "role", "id", "integer"),
    ]

    # Keyed on the retyped column and the new FK column — neither of which the
    # old shape can produce, so this only reads as "applied" once it has run.
    postconditions = [
        column_type_is("macrostrat_auth", "role", "id", "text"),
        has_columns("macrostrat_auth", "role", "postgres_role"),
        has_columns("macrostrat_auth", "user", "role"),
    ]

    # Rewrites rows in `user`, not just structure.
    destructive = True

    # Dev-only until it has been rehearsed against a staging clone.
    readiness_state = "alpha"
