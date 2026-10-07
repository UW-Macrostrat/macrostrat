-- @subsystem: ecosystem
-- @depends-on: core
/**
 * The people directory behind the website's /community page: who has worked
 * on Macrostrat, in which roles, with which contributions.
 *
 * Applied in local, development and staging (see `_STAGING_ENVS` in
 * schema_management/chunks.py) rather than development only, because the
 * public website reads it. The directory is public to read through the
 * macrostrat_api views; changing it is an administrator's job, and a signed-in
 * user (web_user) is never granted a write.
 */

CREATE SCHEMA ecosystem;

CREATE TABLE ecosystem.contributions (
    contribution_id integer NOT NULL,
    person_id integer NOT NULL,
    contribution text NOT NULL,
    description text,
    date timestamp with time zone DEFAULT now() NOT NULL,
    url text
);

CREATE SEQUENCE ecosystem.contributions_contribution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

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

CREATE TABLE ecosystem.people_contributions (
    person_id integer NOT NULL,
    contribution_id integer NOT NULL
);

CREATE SEQUENCE ecosystem.people_person_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE ecosystem.people_person_id_seq OWNED BY ecosystem.people.person_id;

CREATE TABLE ecosystem.people_roles (
    person_id integer NOT NULL,
    role_id integer NOT NULL
);

CREATE TABLE ecosystem.roles (
    role_id integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL
);

CREATE SEQUENCE ecosystem.roles_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

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

-- The people directory is public to read; changing it is an administrator's job.
GRANT SELECT ON TABLE ecosystem.people TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE ecosystem.people TO web_admin;

GRANT SELECT,USAGE ON SEQUENCE ecosystem.people_person_id_seq TO web_admin;

GRANT SELECT ON TABLE ecosystem.people_roles TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE ecosystem.people_roles TO web_admin;


-- ---------------------------------------------------------------------------
-- PostgREST surface. `macrostrat_api` is created by core.
-- ---------------------------------------------------------------------------

CREATE VIEW macrostrat_api.people AS
 SELECT people.person_id,
    people.name,
    people.email,
    people.title,
    people.website,
    people.img_id,
    people.active_start,
    people.active_end
   FROM ecosystem.people;

CREATE VIEW macrostrat_api.people_roles AS
 SELECT people_roles.person_id,
    people_roles.role_id
   FROM ecosystem.people_roles;

CREATE VIEW macrostrat_api.people_with_roles AS
 SELECT p.person_id,
    p.name,
    p.email,
    p.title,
    p.website,
    p.img_id,
    p.active_start,
    p.active_end,
    COALESCE(json_agg(json_build_object('name', r.name, 'description', r.description)) FILTER (WHERE (r.role_id IS NOT NULL))) AS roles
   FROM ((ecosystem.people p
     LEFT JOIN ecosystem.people_roles pr ON ((p.person_id = pr.person_id)))
     LEFT JOIN ecosystem.roles r ON ((pr.role_id = r.role_id)))
  GROUP BY p.person_id;

GRANT SELECT ON TABLE macrostrat_api.people TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE macrostrat_api.people TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.people_roles TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE macrostrat_api.people_roles TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.people_with_roles TO web_anon;
