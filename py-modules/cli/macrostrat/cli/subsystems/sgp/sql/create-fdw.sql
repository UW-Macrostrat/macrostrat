/** Create a foreign data wrapper for the SGP database */
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

DROP SERVER IF EXISTS sgp_server CASCADE;
CREATE SERVER IF NOT EXISTS sgp_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host :sgp_host, dbname :sgp_database, port :sgp_port);

/** Create a user mapping for the SGP database */
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
  SERVER sgp_server
  OPTIONS (user :sgp_user, password :sgp_password);

CREATE SCHEMA IF NOT EXISTS sgp;
IMPORT FOREIGN SCHEMA public FROM SERVER sgp_server INTO sgp;
