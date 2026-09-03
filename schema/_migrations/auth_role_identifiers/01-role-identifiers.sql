/* Carry an integer-keyed macrostrat_auth.role over to the string-keyed shape.

   Written to be re-runnable: the steps that read the old shape are guarded on
   the old column still being there, and the role table is rebuilt rather than
   retyped in place (it is a three-row reference table, and an in-place
   ALTER TYPE would have to drop and restore the FK anyway). */

-- 1. Stage the new, semantic role name on `user`, resolved through the old FK.
--    The legacy names were the Postgres role names themselves; `test-only` was
--    the synthetic test account's role.
ALTER TABLE macrostrat_auth."user" ADD COLUMN IF NOT EXISTS role text;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'macrostrat_auth'
      AND table_name = 'user'
      AND column_name = 'role_id'
  ) THEN
    UPDATE macrostrat_auth."user" u
    SET role = CASE r.name
        WHEN 'web_admin' THEN 'admin'
        WHEN 'web_user'  THEN 'user'
        WHEN 'test-only' THEN 'test'
        ELSE 'user'
    END
    FROM macrostrat_auth.role r
    WHERE r.id = u.role_id
      AND u.role IS NULL;

    -- 2. Drop the old FK column; nothing references `role.id` after this.
    ALTER TABLE macrostrat_auth."user" DROP COLUMN role_id;
  END IF;
END
$$;

-- Any user whose role_id pointed nowhere (or whose row predates the FK) lands
-- in the default role rather than blocking the NOT NULL below.
UPDATE macrostrat_auth."user" SET role = 'user' WHERE role IS NULL;

-- 3. Rebuild the lookup table with the name as its key. Dropping it takes the
--    `role_id_seq` sequence with it.
DROP TABLE IF EXISTS macrostrat_auth.role;

CREATE TABLE macrostrat_auth.role (
    id            text primary key,
    postgres_role text not null,
    description   text
);

INSERT INTO macrostrat_auth.role (id, postgres_role, description) VALUES
    ('user',  'web_user',  'A signed-in Macrostrat user'),
    ('admin', 'web_admin', 'A Macrostrat administrator'),
    ('test',  'web_user',  'A synthetic account used by the test suite')
ON CONFLICT (id) DO UPDATE
    SET postgres_role = EXCLUDED.postgres_role,
        description   = EXCLUDED.description;

-- 4. Anything that survived step 1 with a role outside the canonical set would
--    fail the FK; fold it into the default role first.
UPDATE macrostrat_auth."user" u
SET role = 'user'
WHERE NOT EXISTS (SELECT 1 FROM macrostrat_auth.role r WHERE r.id = u.role);

ALTER TABLE macrostrat_auth."user" ALTER COLUMN role SET NOT NULL;

ALTER TABLE macrostrat_auth."user"
    DROP CONSTRAINT IF EXISTS user_role_fkey;
ALTER TABLE macrostrat_auth."user"
    ADD CONSTRAINT user_role_fkey FOREIGN KEY (role) REFERENCES macrostrat_auth.role(id);
