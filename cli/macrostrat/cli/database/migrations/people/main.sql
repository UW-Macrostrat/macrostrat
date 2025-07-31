CREATE SCHEMA ecosystem;

CREATE TABLE IF NOT EXISTS ecosystem.people (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    title text NOT NULL,
    website text,
    img_id text,
    roles integer[] NOT NULL DEFAULT '{}',
    active_start timestamp with time zone NOT NULL DEFAULT now(),
    active_end timestamp with time zone,
);

CREATE TABLE IF NOT EXISTS ecosystem.roles (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text NOT NULL
);

CREATE TABLE IF NOT EXISTS ecosystem.people_roles (
    person_id integer NOT NULL REFERENCES ecosystem.people(id) ON DELETE CASCADE,
    role_id integer NOT NULL REFERENCES ecosystem.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, role_id)
);

CREATE TABLE IF NOT EXISTS ecosystem.contributions (
    id serial PRIMARY KEY,
    person_id integer NOT NULL REFERENCES macrostrat.people(id) ON DELETE CASCADE,
    contribution text NOT NULL,
    rockd boolean NOT NULL DEFAULT false,
    macrostrat boolean NOT NULL DEFAULT false,
    date timestamp with time zone NOT NULL DEFAULT now(),
    url text
);