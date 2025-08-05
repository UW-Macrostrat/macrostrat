
 -- SCHEMA
CREATE SCHEMA IF NOT EXISTS ecosystem;

-- PEOPLE
CREATE TABLE IF NOT EXISTS ecosystem.people (
    person_id serial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    title text NOT NULL,
    website text,
    img_id text,
    active_start timestamp with time zone DEFAULT now(),
    active_end timestamp with time zone
);

-- ROLES
CREATE TABLE IF NOT EXISTS ecosystem.roles (
    role_id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text NOT NULL
);

-- PEOPLE-ROLES MAPPING
CREATE TABLE IF NOT EXISTS ecosystem.people_roles (
    person_id integer NOT NULL REFERENCES ecosystem.people(person_id) ON DELETE CASCADE,
    role_id integer NOT NULL REFERENCES ecosystem.roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, role_id)
);

-- CONTRIBUTIONS
CREATE TABLE IF NOT EXISTS ecosystem.contributions (
    contribution_id serial PRIMARY KEY,
    person_id integer NOT NULL REFERENCES ecosystem.people(person_id) ON DELETE CASCADE,
    contribution text NOT NULL,
    description text,
    date timestamp with time zone NOT NULL DEFAULT now(),
    url text
);

-- PEOPLE-CONTRIBUTIONS MAPPING
CREATE TABLE IF NOT EXISTS ecosystem.people_contributions (
    person_id integer NOT NULL REFERENCES ecosystem.people(person_id) ON DELETE CASCADE,
    contribution_id integer NOT NULL REFERENCES ecosystem.contributions(contribution_id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, contribution_id)
);

-- PREPOPULATE ROLES
INSERT INTO ecosystem.roles (name, description) VALUES
  ('Student', 'Currently enrolled in an academic program'),
  ('Researcher', 'Conducts academic or applied research'),
  ('Developer', 'Writes and maintains software code'),
  ('Leader', 'Leads research or development projects and mentors others'),
  ('Collaborator', 'Contributes to joint projects')
ON CONFLICT (name) DO NOTHING;

-- CREATE POSTGREST VIEWS
CREATE OR REPLACE VIEW macrostrat_api.people AS
	SELECT * FROM ecosystem.people;

CREATE OR REPLACE VIEW macrostrat_api.people_roles AS
	SELECT * FROM ecosystem.people_roles;

CREATE OR REPLACE VIEW macrostrat_api.people_with_roles AS
	SELECT p.id,
	    p.name,
	    p.email,
	    p.title,
	    p.website,
	    p.img_id,
	    p.active_start,
	    p.active_end,
	    COALESCE(json_agg(json_build_object('name', r.name, 'description', r.description)) FILTER (WHERE r.id IS NOT NULL)) AS roles
	   FROM ecosystem.people p
	     LEFT JOIN ecosystem.people_roles pr ON p.id = pr.person_id
	     LEFT JOIN ecosystem.roles r ON pr.role_id = r.id
	  GROUP BY p.id;


-- DEFAULT PRIVILEGES
GRANT SELECT, INSERT, UPDATE, DELETE ON 
	ecosystem.people, 
	ecosystem.people_roles,
	macrostrat_api.people, 
	macrostrat_api.people_roles
TO web_anon;

GRANT USAGE, SELECT ON SEQUENCE ecosystem.people_person_id_seq TO web_anon;