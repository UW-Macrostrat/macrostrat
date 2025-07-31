CREATE TABLE IF NOT EXISTS macrostrat.people (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    title text NOT NULL,
    website text,
    img_id text,
    student boolean NOT NULL DEFAULT false,
    researcher boolean NOT NULL DEFAULT false,
    developer boolean NOT NULL DEFAULT false,
    postdoc boolean NOT NULL DEFAULT false,
    research_scientist boolean NOT NULL DEFAULT false,
    former boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS macrostrat.contributions (
    id serial PRIMARY KEY,
    person_id integer NOT NULL REFERENCES macrostrat.people(id) ON DELETE CASCADE,
    contribution text NOT NULL,
    rockd boolean NOT NULL DEFAULT false,
    macrostrat boolean NOT NULL DEFAULT false,
    date_created timestamp with time zone NOT NULL DEFAULT now()
);