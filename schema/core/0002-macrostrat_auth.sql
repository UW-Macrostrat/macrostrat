
CREATE SCHEMA macrostrat_auth;
ALTER SCHEMA macrostrat_auth OWNER TO macrostrat;

CREATE FUNCTION macrostrat_auth.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int
$$;
ALTER FUNCTION macrostrat_auth.current_app_user_id() OWNER TO macrostrat_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE macrostrat_auth."group" (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);
ALTER TABLE macrostrat_auth."group" OWNER TO macrostrat;

CREATE SEQUENCE macrostrat_auth.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_auth.group_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.group_id_seq OWNED BY macrostrat_auth."group".id;

CREATE TABLE macrostrat_auth.group_members (
    id integer NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL
);
ALTER TABLE macrostrat_auth.group_members OWNER TO macrostrat;

CREATE SEQUENCE macrostrat_auth.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_auth.group_members_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.group_members_id_seq OWNED BY macrostrat_auth.group_members.id;

CREATE TABLE macrostrat_auth.token (
    id integer NOT NULL,
    token character varying(255) NOT NULL,
    "group" integer NOT NULL,
    used_on timestamp with time zone,
    expires_on timestamp with time zone NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE macrostrat_auth.token OWNER TO macrostrat;

CREATE SEQUENCE macrostrat_auth.token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_auth.token_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.token_id_seq OWNED BY macrostrat_auth.token.id;

CREATE TABLE macrostrat_auth."user" (
    id integer NOT NULL,
    sub character varying(255) NOT NULL,
    name character varying(255),
    email character varying(255),
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE macrostrat_auth."user" OWNER TO macrostrat;

CREATE SEQUENCE macrostrat_auth.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_auth.user_id_seq OWNER TO macrostrat;

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

