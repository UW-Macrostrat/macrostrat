--
-- PostgreSQL database dump
--

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: macrostrat_auth; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA macrostrat_auth;


ALTER SCHEMA macrostrat_auth OWNER TO macrostrat;

--
-- Name: current_app_user_id(); Type: FUNCTION; Schema: macrostrat_auth; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat_auth.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int
$$;


ALTER FUNCTION macrostrat_auth.current_app_user_id() OWNER TO "macrostrat-admin";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: group; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth."group" (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


ALTER TABLE macrostrat_auth."group" OWNER TO macrostrat;

--
-- Name: group_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE SEQUENCE macrostrat_auth.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_auth.group_id_seq OWNER TO macrostrat;

--
-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER SEQUENCE macrostrat_auth.group_id_seq OWNED BY macrostrat_auth."group".id;


--
-- Name: group_members; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth.group_members (
    id integer NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE macrostrat_auth.group_members OWNER TO macrostrat;

--
-- Name: group_members_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE SEQUENCE macrostrat_auth.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_auth.group_members_id_seq OWNER TO macrostrat;

--
-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER SEQUENCE macrostrat_auth.group_members_id_seq OWNED BY macrostrat_auth.group_members.id;


--
-- Name: token; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth.token (
    id integer NOT NULL,
    token character varying(255) NOT NULL,
    "group" integer NOT NULL,
    used_on timestamp with time zone,
    expires_on timestamp with time zone NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE macrostrat_auth.token OWNER TO macrostrat;

--
-- Name: token_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE SEQUENCE macrostrat_auth.token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_auth.token_id_seq OWNER TO macrostrat;

--
-- Name: token_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER SEQUENCE macrostrat_auth.token_id_seq OWNED BY macrostrat_auth.token.id;


--
-- Name: user; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TABLE macrostrat_auth."user" (
    id integer NOT NULL,
    sub character varying(255) NOT NULL,
    name character varying(255),
    email character varying(255),
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE macrostrat_auth."user" OWNER TO macrostrat;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE SEQUENCE macrostrat_auth.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_auth.user_id_seq OWNER TO macrostrat;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER SEQUENCE macrostrat_auth.user_id_seq OWNED BY macrostrat_auth."user".id;


--
-- Name: group id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth."group" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_id_seq'::regclass);


--
-- Name: group_members id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.group_members ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_members_id_seq'::regclass);


--
-- Name: token id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.token ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.token_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth."user" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.user_id_seq'::regclass);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);


--
-- Name: group group_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth."group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);


--
-- Name: token token_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_pkey PRIMARY KEY (id);


--
-- Name: token token_token_key; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_token_key UNIQUE (token);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user update_updated_on_trigger; Type: TRIGGER; Schema: macrostrat_auth; Owner: macrostrat
--

CREATE TRIGGER update_updated_on_trigger BEFORE UPDATE ON macrostrat_auth."user" FOR EACH ROW WHEN ((old.* IS DISTINCT FROM new.*)) EXECUTE FUNCTION public.update_updated_on();


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES macrostrat_auth."group"(id);


--
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id);


--
-- Name: token token_group_fkey; Type: FK CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_group_fkey FOREIGN KEY ("group") REFERENCES macrostrat_auth."group"(id);


--
-- PostgreSQL database dump complete
--

