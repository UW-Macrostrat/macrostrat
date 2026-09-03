
CREATE SCHEMA macrostrat_auth;

-- Derive the integer user id from the JWT `sub` (ORCID) claim.
SET check_function_bodies = off;
CREATE OR REPLACE FUNCTION macrostrat_auth.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog
    AS $$
  SELECT id
  FROM macrostrat_auth."user"
  WHERE sub = current_setting('request.jwt.claims', true)::json ->> 'sub';
$$;
SET check_function_bodies = on;
ALTER FUNCTION macrostrat_auth.current_app_user_id() OWNER TO macrostrat;
GRANT EXECUTE ON FUNCTION macrostrat_auth.current_app_user_id() TO web_anon, web_user, web_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

-- Application roles. The primary key is the role's own name, so a user's role
-- reads as `'admin'` at every call site instead of an opaque integer that has
-- to be joined back before it means anything. There is deliberately no default:
-- whoever creates a user has to say which role it gets.
CREATE TABLE macrostrat_auth.role (
    id            text primary key,
    -- The Postgres role a session in this application role assumes. PostgREST
    -- reads it from the JWT `role` claim, and the RLS policies and grants are
    -- written against these names, so the mapping is data here rather than a
    -- convention buried in the API.
    postgres_role text not null,
    description   text
);

-- Seeded, not defaulted. `ON CONFLICT ... DO UPDATE` (rather than DO NOTHING)
-- so `macrostrat schema sync` converges the mapping columns too, not just the
-- set of role names.
INSERT INTO macrostrat_auth.role (id, postgres_role, description) VALUES
    ('user',  'web_user',  'A signed-in Macrostrat user'),
    ('admin', 'web_admin', 'A Macrostrat administrator'),
    ('test',  'web_user',  'A synthetic account used by the test suite')
ON CONFLICT (id) DO UPDATE
    SET postgres_role = EXCLUDED.postgres_role,
        description   = EXCLUDED.description;

--user has to be in quotes since it's a postgresql keyword
CREATE TABLE macrostrat_auth."user" (
    id           serial primary key,
    sub          text not null unique,
    name         text,
    email        text,
    display_name text,
    role         text not null references macrostrat_auth.role(id),
    created_on   timestamp with time zone default now() not null,
    updated_on   timestamp with time zone default now() not null
);

CREATE TABLE macrostrat_auth.token (
    id         serial primary key,
    token      text not null unique,
    user_id    integer references macrostrat_auth."user"(id),
    created_by integer references macrostrat_auth."user"(id),
    token_type text not null default 'api',
    label      text,
    scopes     text[],
    used_on    timestamp with time zone,
    expires_on timestamp with time zone not null,
    created_on timestamp with time zone default now() not null,

    --the token is delegated to a Macrostrat user, or to a third party with no account (in
    --if issued to 3rd party with no account, then label must be populated
    constraint token_has_subject check (user_id is not null or label is not null)
);

CREATE TRIGGER update_updated_on_trigger BEFORE UPDATE ON macrostrat_auth."user" FOR EACH ROW WHEN ((old.* IS DISTINCT FROM new.*)) EXECUTE FUNCTION public.update_updated_on();

-- "One live token per label" cannot be an index: a partial index predicated on
-- `expires_on > now()` is rejected (42P17, now() is STABLE not IMMUTABLE), and
-- a plain UNIQUE on label would block reissuing after a revocation, since
-- revoked rows are kept for the record. Enforced in the API and CLI instead.