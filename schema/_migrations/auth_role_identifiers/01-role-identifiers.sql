/* Carry an integer-keyed `macrostrat_auth.role` over to the string-keyed shape
   declared in `schema/core/0002-macrostrat_auth.sql`.

   The lookup table is rebuilt rather than retyped in place: the keys change
   value (1 -> 'admin'), so all three rows are rewritten either way, and an
   in-place ALTER TYPE would still have to drop and restore the foreign key
   from `user`. */

-- Resolve each user's role through the old FK while it is still there. The
-- legacy role names were the Postgres role names themselves, plus `test-only`
-- for the synthetic test account.
ALTER TABLE macrostrat_auth."user" ADD COLUMN role text;

UPDATE macrostrat_auth."user" u
SET role = CASE r.name
    WHEN 'web_admin' THEN 'admin'
    WHEN 'test-only' THEN 'test'
    ELSE 'user'
END
FROM macrostrat_auth.role r
WHERE r.id = u.role_id;

-- Takes the foreign key to `role.id` with it, which is what frees the rebuild.
ALTER TABLE macrostrat_auth."user" DROP COLUMN role_id;

DROP TABLE macrostrat_auth.role;

CREATE TABLE macrostrat_auth.role (
    id            text primary key,
    postgres_role text not null
        constraint role_postgres_role_is_a_web_role
        check (postgres_role in ('web_user', 'web_admin', 'web_anon')),
    description   text
);

INSERT INTO macrostrat_auth.role (id, postgres_role, description) VALUES
    ('user',  'web_user',  'A signed-in Macrostrat user'),
    ('admin', 'web_admin', 'A Macrostrat administrator'),
    ('test',  'web_user',  'A synthetic account used by the test suite')
ON CONFLICT (id) DO UPDATE
    SET postgres_role = EXCLUDED.postgres_role,
        description   = EXCLUDED.description;

-- Constraint names match the ones the declarative build generates, so a later
-- schema diff sees no drift between a migrated and a freshly built database.
ALTER TABLE macrostrat_auth."user"
    ALTER COLUMN role SET NOT NULL,
    ADD CONSTRAINT user_role_fkey FOREIGN KEY (role) REFERENCES macrostrat_auth.role(id);

-- `user` is exposed through PostgREST, and its column set just changed.
NOTIFY pgrst, 'reload schema';
