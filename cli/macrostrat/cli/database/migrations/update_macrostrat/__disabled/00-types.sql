/** TODO: it might be useful to put some logic around these to run them conditionally, add types if necessary. */
CREATE TYPE measurement_class AS ENUM(
  '','geophysical','geochemical','sedimentological');
CREATE TYPE measurement_type AS ENUM(
  '','material properties','geochronological','major elements','minor elements',
  'radiogenic isotopes','stable isotopes','petrologic','environmental');

CREATE TYPE boundary_type AS ENUM('','unconformity','conformity','fault','disconformity','non-conformity','angular unconformity');

CREATE TYPE boundary_status AS ENUM('','modeled','relative','absolute','spike');
