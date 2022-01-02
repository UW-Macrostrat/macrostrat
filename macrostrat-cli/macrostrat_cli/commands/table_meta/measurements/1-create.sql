DROP TYPE IF EXISTS measurement_class CASCADE;
DROP TYPE IF EXISTS measurement_type CASCADE;

CREATE TYPE measurement_class AS ENUM(
  '','geophysical','geochemical','sedimentological');
CREATE TYPE measurement_type AS ENUM(
  '','material properties','geochronological','major elements','minor elements',
  'radiogenic isotopes','stable isotopes','petrologic','environmental');
COMMIT;

CREATE TABLE macrostrat.measurements_new (
  id serial PRIMARY KEY NOT NULL,
  measurement_class measurement_class NOT NULL,
  measurement_type measurement_type NOT NULL,
  measurement text NOT NULL
);
