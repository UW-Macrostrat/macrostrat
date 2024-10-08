/**
  macrostrat_xdd schema

  Fixtures for the macrostrat_xdd schema.
 */

CREATE TABLE macrostrat_xdd.entity_type (
  id          integer GENERATED ALWAYS AS IDENTITY
    PRIMARY KEY,
  name        text NOT NULL,
  description text,
  color       text
);
