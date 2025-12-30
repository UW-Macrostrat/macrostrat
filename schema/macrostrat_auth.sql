--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: group; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS "group" (
    id SERIAL,
    name varchar(255) NOT NULL,
    CONSTRAINT group_pkey PRIMARY KEY (id)
);

--
-- Name: token; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS token (
    id SERIAL,
    token varchar(255) NOT NULL,
    "group" integer NOT NULL,
    used_on timestamptz,
    expires_on timestamptz NOT NULL,
    created_on timestamptz DEFAULT now() NOT NULL,
    CONSTRAINT token_pkey PRIMARY KEY (id),
    CONSTRAINT token_token_key UNIQUE (token),
    CONSTRAINT token_group_fkey FOREIGN KEY ("group") REFERENCES "group" (id)
);

--
-- Name: user; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL,
    sub varchar(255) NOT NULL,
    name varchar(255),
    email varchar(255),
    created_on timestamptz DEFAULT now() NOT NULL,
    updated_on timestamptz DEFAULT now() NOT NULL,
    CONSTRAINT user_pkey PRIMARY KEY (id)
);

--
-- Name: group_members; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS group_members (
    id SERIAL,
    group_id integer NOT NULL,
    user_id integer NOT NULL,
    CONSTRAINT group_members_pkey PRIMARY KEY (id),
    CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES "group" (id),
    CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user" (id)
);

--
-- Name: current_app_user_id(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION current_app_user_id()
RETURNS integer
LANGUAGE sql
STABLE
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int
$$;

--
-- Name: update_updated_on_trigger; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER update_updated_on_trigger
    BEFORE UPDATE ON "user"
    FOR EACH ROW
    WHEN (((OLD.* IS DISTINCT FROM NEW.*)))
    EXECUTE FUNCTION update_updated_on();

