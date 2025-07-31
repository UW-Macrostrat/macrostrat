CREATE TABLE IF NOT EXISTS macrostrat.people (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    title text NOT NULL,
    website text,
    student boolean NOT NULL DEFAULT false,
    researcher boolean NOT NULL DEFAULT false,
    developer boolean NOT NULL DEFAULT false,
    postdoc boolean NOT NULL DEFAULT false,
    research_scientist boolean NOT NULL DEFAULT false,
    former boolean NOT NULL DEFAULT false
);