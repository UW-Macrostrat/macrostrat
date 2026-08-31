
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

CREATE TABLE macrostrat_auth.role (
    id   serial primary key,
    name text not null unique
);

INSERT INTO macrostrat_auth.role (id, name) VALUES
    (1, 'web_admin'),
    (2, 'test-only'),
    (3, 'web_user')
ON CONFLICT (id) DO NOTHING;

SELECT setval('macrostrat_auth.role_id_seq', (SELECT max(id) FROM macrostrat_auth.role));

--user has to be in quotes since it's a postgresql keyword
CREATE TABLE macrostrat_auth."user" (
    id           serial primary key,
    sub          text not null unique,
    name         text,
    email        text,
    display_name text,
    role_id      integer not null references macrostrat_auth.role(id),
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

GRANT USAGE ON SCHEMA macrostrat_auth TO macrostrat;
GRANT SELECT ON macrostrat_auth."user" TO macrostrat;

CREATE TRIGGER update_updated_on_trigger BEFORE UPDATE ON macrostrat_auth."user" FOR EACH ROW WHEN ((old.* IS DISTINCT FROM new.*)) EXECUTE FUNCTION public.update_updated_on();

CREATE UNIQUE INDEX token_label_live_key
    ON macrostrat_auth.token (label)
    WHERE expires_on > now();