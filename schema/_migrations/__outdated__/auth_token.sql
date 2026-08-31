--Ran manually 8/31/26; afromandi

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. group -> role. The rows are Postgres roles, not groups.
-- ---------------------------------------------------------------------------

ALTER TABLE macrostrat_auth."group" RENAME TO role;
ALTER SEQUENCE macrostrat_auth.group_id_seq RENAME TO role_id_seq;
ALTER TABLE macrostrat_auth.role RENAME CONSTRAINT group_pkey TO role_pkey;

-- varchar(255) -> text is binary-coercible, so no table rewrite. Done before
-- the unique constraint so that index is built once, on the final type.
ALTER TABLE macrostrat_auth.role ALTER COLUMN name TYPE text;
ALTER TABLE macrostrat_auth.role ADD CONSTRAINT role_name_key UNIQUE (name);

-- ---------------------------------------------------------------------------
-- 2. One role per user, lifted off group_members before it is dropped.
-- ---------------------------------------------------------------------------

ALTER TABLE macrostrat_auth."user"
    ALTER COLUMN sub          TYPE text,
    ALTER COLUMN name         TYPE text,
    ALTER COLUMN email        TYPE text,
    ALTER COLUMN display_name TYPE text,
    ADD COLUMN role_id integer REFERENCES macrostrat_auth.role(id);

-- Faithful translation of the mint-time role computation in security.py:
-- admin if in a group named web_admin/admin or group id 1, else web_user.
-- No user's effective role changes.
UPDATE macrostrat_auth."user" u SET role_id = CASE
    WHEN EXISTS (
        SELECT 1
        FROM macrostrat_auth.group_members gm
        JOIN macrostrat_auth.role r ON r.id = gm.group_id
        WHERE gm.user_id = u.id
          AND (r.name IN ('web_admin', 'admin') OR r.id = 1)
    )
    THEN (SELECT id FROM macrostrat_auth.role WHERE name = 'web_admin')
    ELSE (SELECT id FROM macrostrat_auth.role WHERE name = 'web_user')
END;

ALTER TABLE macrostrat_auth."user" ALTER COLUMN role_id SET NOT NULL;

DROP TABLE macrostrat_auth.group_members;

-- ---------------------------------------------------------------------------
-- 3. Tokens delegate a user's authority, or belong to a labelled third party.
-- ---------------------------------------------------------------------------

-- token_type may already exist: it has been in the ORM (api/schemas.py)
-- without ever being in the declarative schema.
ALTER TABLE macrostrat_auth.token
    ALTER COLUMN token TYPE text,
    ADD COLUMN IF NOT EXISTS user_id    integer REFERENCES macrostrat_auth."user"(id),
    ADD COLUMN IF NOT EXISTS created_by integer REFERENCES macrostrat_auth."user"(id),
    ADD COLUMN IF NOT EXISTS token_type text NOT NULL DEFAULT 'api',
    ADD COLUMN IF NOT EXISTS label      text,
    ADD COLUMN IF NOT EXISTS scopes     text[];

-- Every pre-existing token is bcrypt-hashed and cannot be validated under the
-- sha256 scheme, so none can authenticate any more regardless. Kept for audit:
-- labelled so they satisfy token_has_subject, and expired so they are unusable
-- by construction rather than only by hash mismatch.
UPDATE macrostrat_auth.token
SET label      = 'legacy group token, group ' || "group",
    expires_on = least(expires_on, now())
WHERE label IS NULL
  AND user_id IS NULL;

ALTER TABLE macrostrat_auth.token
    ADD CONSTRAINT token_has_subject
        CHECK (user_id IS NOT NULL OR label IS NOT NULL);

ALTER TABLE macrostrat_auth.token
    DROP CONSTRAINT IF EXISTS token_group_fkey,
    DROP COLUMN IF EXISTS "group";

COMMIT;
