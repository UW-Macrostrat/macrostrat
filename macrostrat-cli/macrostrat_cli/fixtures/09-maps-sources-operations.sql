/** Create primary keys for maps tables */

ALTER TABLE maps.sources ADD PRIMARY KEY (source_id);
-- Make slug not null and unique (Postgres)
ALTER TABLE maps.sources ALTER COLUMN slug SET NOT NULL;
ALTER TABLE maps.sources ADD UNIQUE (slug);

/** Create table for tracking map management operations */
CREATE TABLE IF NOT EXISTS maps.source_operations (
    id SERIAL NOT NULL PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id) ON DELETE CASCADE,
    -- If applicable, which application user performed the operation
    user_id integer REFERENCES macrostrat_auth.user(id) ON DELETE SET NULL,
    operation text NOT NULL,
    app text NOT NULL,
    comments text,
    details jsonb,
    date timestamp with time zone DEFAULT now() NOT NULL
);

/** Should also create a 'maps.source_files' table or similar to link to the files schema */

COMMENT ON TABLE maps.source_operations IS 'Tracks management operations for Macrostrat maps';