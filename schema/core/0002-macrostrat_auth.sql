
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

CREATE TABLE macrostrat_auth."group" (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

CREATE SEQUENCE macrostrat_auth.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat_auth.group_id_seq OWNED BY macrostrat_auth."group".id;

CREATE TABLE macrostrat_auth.group_members (
    id integer NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL
);

CREATE SEQUENCE macrostrat_auth.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat_auth.group_members_id_seq OWNED BY macrostrat_auth.group_members.id;

CREATE TABLE macrostrat_auth.token (
    id integer NOT NULL,
    token character varying(255) NOT NULL,
    "group" integer NOT NULL,
    used_on timestamp with time zone,
    expires_on timestamp with time zone NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE macrostrat_auth.token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat_auth.token_id_seq OWNED BY macrostrat_auth.token.id;

CREATE TABLE macrostrat_auth."user" (
    id           serial primary key,
    sub          varchar(255) not null unique,
    name         varchar(255),
    email        varchar(255),
    display_name varchar(255),
    created_on   timestamp with time zone default now() not null,
    updated_on   timestamp with time zone default now() not null
);

-- current_app_user_id() is SECURITY DEFINER owned by `macrostrat`, but this
-- schema/table are owned by the (superuser) `macrostrat_admin`. Grant the
-- definer role just enough to resolve sub → id: read-only on this one table.
-- (Owning the function with `macrostrat` rather than the superuser keeps the
-- definer least-privilege.)
GRANT USAGE ON SCHEMA macrostrat_auth TO macrostrat;
GRANT SELECT ON macrostrat_auth."user" TO macrostrat;

CREATE SEQUENCE macrostrat_auth.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat_auth.user_id_seq OWNED BY macrostrat_auth."user".id;

ALTER TABLE ONLY macrostrat_auth."group" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_auth.group_members ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_members_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_auth.token ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.token_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_auth."user" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.user_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_auth."group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_token_key UNIQUE (token);

ALTER TABLE ONLY macrostrat_auth."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);

CREATE TRIGGER update_updated_on_trigger BEFORE UPDATE ON macrostrat_auth."user" FOR EACH ROW WHEN ((old.* IS DISTINCT FROM new.*)) EXECUTE FUNCTION public.update_updated_on();

ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES macrostrat_auth."group"(id);

ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id);

ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_group_fkey FOREIGN KEY ("group") REFERENCES macrostrat_auth."group"(id);

