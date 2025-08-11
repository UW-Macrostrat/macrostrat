/** Create a foreign data wrapper for the SGP database */
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

CREATE SERVER IF NOT EXISTS sgp_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host 'localhost', dbname 'sgp', port '5432');

/** Create a user mapping for the SGP database */
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
  SERVER sgp_server;

CREATE SCHEMA IF NOT EXISTS sgp;
IMPORT FOREIGN SCHEMA public FROM SERVER sgp_server INTO sgp;
