/** SQL run during a mostly manual conversion of the knowledge graph database (2024-09-11)
  *  to use an overall simpler schema. Major changes include:
  *  - Using integer ids instead of UUIDs
  *  - Using an extensible, foreign-keyed table for entity and relationship types (instead of a custom enum)
  *  - Simpler, terser column/table names

  The script is not complete and was run in parts, with manual checks in between.
  There are a few inconsistencies remaining, like
  - A triangular dependency graph between model_run, source_text, and entity/relationship tables.
  - The source_text table contains nearly-identical source text windows that differ only by post-processing,
    which makes it hard to represent different relationships together. this may be a problem with Weaviate
  - We haven't yet figured out how to integrate feedback and the user model.

 */

/** Update entity and relationship tables to use integer ids */

ALTER SCHEMA macrostrat_kg_new RENAME TO macrostrat_xdd;

UPDATE source_text
SET model_run_id = m.id
FROM model_run m
WHERE source_text.run_id = m.run_id_old;

ALTER TABLE source_text ALTER COLUMN model_run_id SET NOT NULL;
ALTER TABLE source_text DROP COLUMN run_id;


UPDATE relationship
SET model_run_id = m.id
FROM model_run m
WHERE relationship.run_id = m.run_id_old;

-- Create foreign key constraints
ALTER TABLE relationship ADD CONSTRAINT fk_model_run_id FOREIGN KEY (model_run_id) REFERENCES model_run(id);
ALTER TABLE relationship ALTER COLUMN model_run_id SET NOT NULL;
ALTER TABLE relationship DROP COLUMN run_id;
-- set unique constraint
ALTER TABLE relationship ADD CONSTRAINT relationship_unique UNIQUE (model_run_id, src_entity_id, dst_entity_id, source_id);


ALTER TABLE entity ADD COLUMN model_run_id integer;
UPDATE entity
SET model_run_id = m.id
FROM model_run m
WHERE entity.run_id = m.run_id_old;

-- Create foreign key constraints
ALTER TABLE entity ADD CONSTRAINT fk_model_run_id FOREIGN KEY (model_run_id) REFERENCES model_run(id);
ALTER TABLE entity ALTER COLUMN model_run_id SET NOT NULL;
ALTER TABLE entity DROP COLUMN run_id;



/** Update entity and relationship tables to use integer ids */
ALTER TABLE entity RENAME COLUMN id TO old_id;
ALTER TABLE entity ADD COLUMN id SERIAL PRIMARY KEY;

ALTER TABLE relationship RENAME COLUMN src_entity_id TO old_src_entity_id;
ALTER TABLE relationship RENAME COLUMN dst_entity_id TO old_dst_entity_id;
ALTER TABLE relationship ADD COLUMN src_entity_id integer;
ALTER TABLE relationship ADD COLUMN dst_entity_id integer;

UPDATE relationship
SET src_entity_id = e.id
FROM entity e
WHERE relationship.old_src_entity_id = e.old_id;

UPDATE relationship
SET dst_entity_id = e.id
FROM entity e
WHERE relationship.old_dst_entity_id = e.old_id;

-- Set not null
ALTER TABLE relationship ALTER COLUMN src_entity_id SET NOT NULL;
ALTER TABLE relationship ALTER COLUMN dst_entity_id SET NOT NULL;

-- Create foreign key constraints
ALTER TABLE relationship ADD CONSTRAINT fk_src_entity_id FOREIGN KEY (src_entity_id) REFERENCES entity(id);
ALTER TABLE relationship ADD CONSTRAINT fk_dst_entity_id FOREIGN KEY (dst_entity_id) REFERENCES entity(id);
ALTER TABLE relationship DROP COLUMN old_src_entity_id;
ALTER TABLE relationship DROP COLUMN old_dst_entity_id;

/** Source IDs */
ALTER TABLE source_text RENAME COLUMN id TO old_id;
ALTER TABLE source_text ADD COLUMN id SERIAL PRIMARY KEY;

ALTER TABLE entity RENAME COLUMN source_id TO old_source_id;
ALTER TABLE entity ADD COLUMN source_id integer;

UPDATE entity
SET source_id = s.id
FROM source_text s
WHERE entity.old_source_id = s.old_id;

-- Set not null
ALTER TABLE entity ALTER COLUMN source_id SET NOT NULL;
-- Create foreign key constraints
ALTER TABLE entity ADD CONSTRAINT fk_source_id FOREIGN KEY (source_id) REFERENCES source_text(id);
ALTER TABLE entity DROP COLUMN old_source_id;


ALTER TABLE relationship RENAME COLUMN source_id TO old_source_id;
ALTER TABLE relationship ADD COLUMN source_id integer;

UPDATE relationship
SET source_id = s.id
FROM source_text s
WHERE relationship.old_source_id = s.old_id;

-- Set not null
ALTER TABLE relationship ALTER COLUMN source_id SET NOT NULL;
-- Create foreign key constraints
ALTER TABLE relationship ADD CONSTRAINT fk_source_id FOREIGN KEY (source_id) REFERENCES source_text(id);

-- set unique constraint
ALTER TABLE entity ADD CONSTRAINT entity_unique UNIQUE (model_run_id, name, type, source_id);
ALTER TABLE relationship ADD CONSTRAINT relationship_unique UNIQUE (model_run_id, src_entity_id, dst_entity_id, source_id);

/** Update entity and relationship types */
ALTER TABLE entity ALTER COLUMN type SET DATA TYPE text USING type::text;
DROP TYPE IF EXISTS entity_type;

CREATE TABLE macrostrat_xdd.entity_type (
    name TEXT NOT NULL PRIMARY KEY,
    description TEXT
);


INSERT INTO macrostrat_xdd.entity_type (name) SELECT DISTINCT type FROM entity;

ALTER TABLE entity ALTER COLUMN type SET NOT NULL;
ALTER TABLE entity ADD CONSTRAINT fk_entity_type FOREIGN KEY (type) REFERENCES macrostrat_xdd.entity_type(name);


ALTER TABLE relationship ALTER COLUMN type SET DATA TYPE text USING type::text;
DROP TYPE IF EXISTS relationship_type;

CREATE TABLE macrostrat_xdd.relationship_type (
    name TEXT NOT NULL PRIMARY KEY,
    description TEXT
);

INSERT INTO macrostrat_xdd.relationship_type (name) SELECT DISTINCT type FROM relationship;

ALTER TABLE relationship ALTER COLUMN type SET NOT NULL;
ALTER TABLE relationship ADD CONSTRAINT fk_relationship_type FOREIGN KEY (type) REFERENCES macrostrat_xdd.relationship_type(name);

/** Link to macrostrat tables */
ALTER TABLE entity
  ADD CONSTRAINT fk_strat_name_id
  FOREIGN KEY (strat_name_id)
  REFERENCES macrostrat.strat_names(id);

ALTER TABLE entity
  ADD CONSTRAINT fk_lith_id
  FOREIGN KEY (lith_id)
  REFERENCES macrostrat.liths(id);

ALTER TABLE entity
  ADD CONSTRAINT fk_lith_att_id
  FOREIGN KEY (lith_att_id)
  REFERENCES macrostrat.lith_atts(id);

/** Try to fill the start_index and end_index columns */
ALTER TABLE entity ADD COLUMN start_index integer;
ALTER TABLE entity ADD COLUMN end_index integer;

UPDATE entity
SET start_index = position(name IN paragraph_text) - 1,
    end_index = position(name IN paragraph_text) + length(name) - 1
FROM source_text s
WHERE entity.source_id = s.id;

ALTER TABLE entity ALTER COLUMN start_index SET NOT NULL;
ALTER TABLE entity ALTER COLUMN end_index SET NOT NULL;

/** Create references table */
CREATE TABLE macrostrat_xdd.publication (
  paper_id text primary key,
  doi text,
  url text,
  citation jsonb not null
);
