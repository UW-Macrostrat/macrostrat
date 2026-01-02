

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

CREATE SCHEMA ecosystem;
ALTER SCHEMA ecosystem OWNER TO macrostrat_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE ecosystem.contributions (
    contribution_id integer NOT NULL,
    person_id integer NOT NULL,
    contribution text NOT NULL,
    description text,
    date timestamp with time zone DEFAULT now() NOT NULL,
    url text
);
ALTER TABLE ecosystem.contributions OWNER TO macrostrat_admin;

CREATE SEQUENCE ecosystem.contributions_contribution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE ecosystem.contributions_contribution_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE ecosystem.contributions_contribution_id_seq OWNED BY ecosystem.contributions.contribution_id;

CREATE TABLE ecosystem.people (
    person_id integer NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    title text NOT NULL,
    website text,
    img_id text,
    active_start timestamp with time zone DEFAULT now(),
    active_end timestamp with time zone
);
ALTER TABLE ecosystem.people OWNER TO macrostrat_admin;

CREATE TABLE ecosystem.people_contributions (
    person_id integer NOT NULL,
    contribution_id integer NOT NULL
);
ALTER TABLE ecosystem.people_contributions OWNER TO macrostrat_admin;

CREATE SEQUENCE ecosystem.people_person_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE ecosystem.people_person_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE ecosystem.people_person_id_seq OWNED BY ecosystem.people.person_id;

CREATE TABLE ecosystem.people_roles (
    person_id integer NOT NULL,
    role_id integer NOT NULL
);
ALTER TABLE ecosystem.people_roles OWNER TO macrostrat_admin;

CREATE TABLE ecosystem.roles (
    role_id integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL
);
ALTER TABLE ecosystem.roles OWNER TO macrostrat_admin;

CREATE SEQUENCE ecosystem.roles_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE ecosystem.roles_role_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE ecosystem.roles_role_id_seq OWNED BY ecosystem.roles.role_id;

ALTER TABLE ONLY ecosystem.contributions ALTER COLUMN contribution_id SET DEFAULT nextval('ecosystem.contributions_contribution_id_seq'::regclass);

ALTER TABLE ONLY ecosystem.people ALTER COLUMN person_id SET DEFAULT nextval('ecosystem.people_person_id_seq'::regclass);

ALTER TABLE ONLY ecosystem.roles ALTER COLUMN role_id SET DEFAULT nextval('ecosystem.roles_role_id_seq'::regclass);

ALTER TABLE ONLY ecosystem.contributions
    ADD CONSTRAINT contributions_pkey PRIMARY KEY (contribution_id);

ALTER TABLE ONLY ecosystem.people_contributions
    ADD CONSTRAINT people_contributions_pkey PRIMARY KEY (person_id, contribution_id);

ALTER TABLE ONLY ecosystem.people
    ADD CONSTRAINT people_email_key UNIQUE (email);

ALTER TABLE ONLY ecosystem.people
    ADD CONSTRAINT people_pkey PRIMARY KEY (person_id);

ALTER TABLE ONLY ecosystem.people_roles
    ADD CONSTRAINT people_roles_pkey PRIMARY KEY (person_id, role_id);

ALTER TABLE ONLY ecosystem.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);

ALTER TABLE ONLY ecosystem.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (role_id);

ALTER TABLE ONLY ecosystem.contributions
    ADD CONSTRAINT contributions_person_id_fkey FOREIGN KEY (person_id) REFERENCES ecosystem.people(person_id) ON DELETE CASCADE;

ALTER TABLE ONLY ecosystem.people_contributions
    ADD CONSTRAINT people_contributions_contribution_id_fkey FOREIGN KEY (contribution_id) REFERENCES ecosystem.contributions(contribution_id) ON DELETE CASCADE;

ALTER TABLE ONLY ecosystem.people_contributions
    ADD CONSTRAINT people_contributions_person_id_fkey FOREIGN KEY (person_id) REFERENCES ecosystem.people(person_id) ON DELETE CASCADE;

ALTER TABLE ONLY ecosystem.people_roles
    ADD CONSTRAINT people_roles_person_id_fkey FOREIGN KEY (person_id) REFERENCES ecosystem.people(person_id) ON DELETE CASCADE;

ALTER TABLE ONLY ecosystem.people_roles
    ADD CONSTRAINT people_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES ecosystem.roles(role_id) ON DELETE CASCADE;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ecosystem.people TO web_anon;

GRANT SELECT,USAGE ON SEQUENCE ecosystem.people_person_id_seq TO web_anon;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE ecosystem.people_roles TO web_anon;

