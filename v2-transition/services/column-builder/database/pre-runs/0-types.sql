CREATE TYPE measurement_class AS ENUM(
  '','geophysical','geochemical','sedimentological');
CREATE TYPE measurement_type AS ENUM(
  '','material properties','geochronological','major elements','minor elements',
  'radiogenic isotopes','stable isotopes','petrologic','environmental');