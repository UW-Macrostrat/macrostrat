--
-- Name: macrostrat_auth; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA macrostrat_auth;
ALTER SCHEMA macrostrat_auth OWNER TO macrostrat;

--
-- Name: group; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth."group" (
    id integer NOT NULL PRIMARY KEY,
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

ALTER SEQUENCE macrostrat_auth.group_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.group_id_seq OWNED BY macrostrat_auth."group".id;

--
-- Name: user; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth."user" (
    id integer NOT NULL PRIMARY KEY,
    sub character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
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

ALTER SEQUENCE macrostrat_auth.user_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.user_id_seq OWNED BY macrostrat_auth."user".id;

--
-- Name: group_members; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth.group_members (
    id integer NOT NULL PRIMARY KEY,
    group_id integer NOT NULL
        REFERENCES macrostrat_auth."group",
    user_id integer NOT NULL
        REFERENCES macrostrat_auth."user"
);


ALTER TABLE macrostrat_auth.group_members OWNER TO macrostrat;

CREATE SEQUENCE macrostrat_auth.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat_auth.group_members_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.group_members_id_seq OWNED BY macrostrat_auth.group_members.id;

--
-- Name: token; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth.token (
    id integer NOT NULL PRIMARY KEY,
    token character varying(255) NOT NULL,
    "group" integer NOT NULL
        REFERENCES macrostrat_auth."group",
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

ALTER SEQUENCE macrostrat_auth.token_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat_auth.token_id_seq OWNED BY macrostrat_auth.token.id;

--
--
--

ALTER TABLE ONLY macrostrat_auth."group" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_id_seq'::regclass);
ALTER TABLE ONLY macrostrat_auth.group_members ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_members_id_seq'::regclass);
ALTER TABLE ONLY macrostrat_auth.token ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.token_id_seq'::regclass);
ALTER TABLE ONLY macrostrat_auth."user" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.user_id_seq'::regclass);

--
-- Name: DATABASE macrostrat; Type: ACL; Schema: -; Owner: macrostrat
--

GRANT ALL ON DATABASE macrostrat TO postgrest;
