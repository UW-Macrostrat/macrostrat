DROP TYPE IF EXISTS measurement_class_new CASCADE;
DROP TYPE IF EXISTS measurement_type_new CASCADE;
CREATE TYPE measurement_class_new AS ENUM('','geophysical','geochemical','sedimentological');
CREATE TYPE measurement_type_new AS ENUM('','material properties','geochronological','major elements','minor elements','radiogenic isotopes','stable isotopes','petrologic','environmental');
CREATE TABLE macrostrat.measurements_new (
  id serial PRIMARY KEY NOT NULL,
  measurement_class measurement_class_new,
  measurement_type measurement_type_new,
  measurement text
);
