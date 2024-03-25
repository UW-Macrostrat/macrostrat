Macrostrat in a Box
===================

An implementation of the Macrostrat platform on a single host


Overview
--------

Macrostrat-in-a-Box uses Docker Compose to start, stop, and orchestrate the
services that make up the Macrostrat platform. It is not intended for
production use, but the Docker Compose setup can be used as inspiration for
a [production system](Macrostrat Online.md).


System Requirements
-------------------

**(NOTE: These requirements are in currently in a state of flux.)**

A host with the following available resources:

* X cores
* Y GiB of RAM
* Z GiB of disk
* [Docker Compose](https://docs.docker.com/compose/)


Steps
-----

**(NOTE: This section is a preview of what is to come.)**

* Clone this GitHub respository.

* Download a database dump file for bootstrapping the system.

* Run the following to start the database:

      docker compose up macrostrat-database -d

* Run the following to import the database dump file:

      docker exec -it macrostrat-database pg_restore ...

* Run the following to create the database's users and password:

      docker exec -it macrostrat-database ...

* Run the following to stop the database:

      docker compose down

* Run the following to create the secrets used by Macrostrat's
  authentication and authorization mechanisms:

      make new-secret-keys

* Run the following to start the whole system:

      docker compose up -d
