/** Create primary keys for maps tables */

ALTER TABLE maps.sources ADD PRIMARY KEY (source_id);
-- Make slug not null and unique (Postgres)
ALTER TABLE maps.sources ALTER COLUMN slug SET NOT NULL;
ALTER TABLE maps.sources ADD UNIQUE (slug);

/** Create table for tracking map management operations */
CREATE TABLE IF NOT EXISTS maps.source_operations (
    id SERIAL NOT NULL PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id),
    user integer REFERENCES macrostrat_auth.user(id),
    app text,
    description text,
    date timestamp with time zone DEFAULT now() NOT NULL
);
