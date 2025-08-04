-- SCHEMA
CREATE SCHEMA IF NOT EXISTS ecosystem;

-- PEOPLE
CREATE TABLE IF NOT EXISTS ecosystem.people (
    id serial PRIMARY KEY,
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
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text NOT NULL
);

-- PEOPLE-ROLES MAPPING
CREATE TABLE IF NOT EXISTS ecosystem.people_roles (
    person_id integer NOT NULL REFERENCES ecosystem.people(id) ON DELETE CASCADE,
    role_id integer NOT NULL REFERENCES ecosystem.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, role_id)
);

-- CONTRIBUTIONS
CREATE TABLE IF NOT EXISTS ecosystem.contributions (
    id serial PRIMARY KEY,
    person_id integer NOT NULL REFERENCES ecosystem.people(id) ON DELETE CASCADE,
    contribution text NOT NULL,
    description text,
    date timestamp with time zone NOT NULL DEFAULT now(),
    url text
);

-- PEOPLE-CONTRIBUTIONS MAPPING
CREATE TABLE IF NOT EXISTS ecosystem.people_contributions (
    person_id integer NOT NULL REFERENCES ecosystem.people(id) ON DELETE CASCADE,
    contribution_id integer NOT NULL REFERENCES ecosystem.contributions(id) ON DELETE CASCADE,
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

-- DEFAULT PRIVILEGES
GRANT SELECT, INSERT, UPDATE, DELETE ON macrostrat_api.people_table, macrostrat_api.people_roles_table TO web_admin;