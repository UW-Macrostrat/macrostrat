DROP TYPE IF EXISTS boundary_type CASCADE;
CREATE TYPE boundary_type AS ENUM('','unconformity','conformity','fault','disconformity','non-conformity','angular unconformity');

DROP TYPE IF EXISTS boundary_status CASCADE;
CREATE TYPE boundary_status AS ENUM('','modeled','relative','absolute','spike');

CREATE TABLE macrostrat.unit_boundaries (
  id serial PRIMARY KEY,
  t1 numeric NOT NULL,
  t1_prop decimal(6,5) NOT NULL,
  t1_age decimal(8,4) NOT NULL,
  unit_id integer NOT NULL,
  unit_id_2 integer NOT NULL,
  section_id integer NOT NULL,
  boundary_position decimal(6,2) DEFAULT NULL,
  boundary_type boundary_type NOT NULL DEFAULT '',
  boundary_status boundary_status NOT NULL DEFAULT 'modeled',
  paleo_lat decimal(8,5),
  paleo_lng decimal(8,5),
  ref_id integer NOT NULL DEFAULT 217,
);