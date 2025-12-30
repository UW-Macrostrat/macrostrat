--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: people; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS people (
    person_id SERIAL,
    name text NOT NULL,
    email text NOT NULL,
    title text NOT NULL,
    website text,
    img_id text,
    active_start timestamptz DEFAULT now(),
    active_end timestamptz,
    CONSTRAINT people_pkey PRIMARY KEY (person_id),
    CONSTRAINT people_email_key UNIQUE (email)
);

--
-- Name: contributions; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS contributions (
    contribution_id SERIAL,
    person_id integer NOT NULL,
    contribution text NOT NULL,
    description text,
    date timestamptz DEFAULT now() NOT NULL,
    url text,
    CONSTRAINT contributions_pkey PRIMARY KEY (contribution_id),
    CONSTRAINT contributions_person_id_fkey FOREIGN KEY (person_id) REFERENCES people (person_id) ON DELETE CASCADE
);

--
-- Name: people_contributions; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS people_contributions (
    person_id integer,
    contribution_id integer,
    CONSTRAINT people_contributions_pkey PRIMARY KEY (person_id, contribution_id),
    CONSTRAINT people_contributions_contribution_id_fkey FOREIGN KEY (contribution_id) REFERENCES contributions (contribution_id) ON DELETE CASCADE,
    CONSTRAINT people_contributions_person_id_fkey FOREIGN KEY (person_id) REFERENCES people (person_id) ON DELETE CASCADE
);

--
-- Name: roles; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL,
    name text NOT NULL,
    description text NOT NULL,
    CONSTRAINT roles_pkey PRIMARY KEY (role_id),
    CONSTRAINT roles_name_key UNIQUE (name)
);

--
-- Name: people_roles; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS people_roles (
    person_id integer,
    role_id integer,
    CONSTRAINT people_roles_pkey PRIMARY KEY (person_id, role_id),
    CONSTRAINT people_roles_person_id_fkey FOREIGN KEY (person_id) REFERENCES people (person_id) ON DELETE CASCADE,
    CONSTRAINT people_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles (role_id) ON DELETE CASCADE
);

