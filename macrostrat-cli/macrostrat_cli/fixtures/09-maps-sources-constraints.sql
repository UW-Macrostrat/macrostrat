/** Create primary keys for maps tables */

ALTER TABLE maps.sources ADD PRIMARY KEY (source_id);
-- Make slug not null and unique (Postgres)
ALTER TABLE maps.sources ALTER COLUMN slug SET NOT NULL;
ALTER TABLE maps.sources ADD UNIQUE (slug);