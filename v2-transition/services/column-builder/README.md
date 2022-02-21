# Stratigraphic Column Data Infrastructure

## About

This application aims to be the next step in data aquistion for stratigraphic columns in macrostrat. The approach taken here is PostgreSQL db centered, the exposed restful api is postgrest, which exists in the application as a docker container (see `docker-compose.yaml`).

The database is an evolution of the current postgres instance of macrostrat from the gunnison server. In `/database/alterations`, you can see several sql files that contain alterations run on the gunnison database to enhance the schema to fully unleash the power of postgresql, this includes things like explicit foreign keys.

The `postgrest` api is built on-top of the `macrostrat_api` schema in the database. This schema is a collection of views built off of the actual data. This approach nicely isolates the core data, in `macrostrat` schema, and the public facing views. This will also help with access control and authentication. A list of all custom views can be found in `/database/fixtures/views.sql`. **NOTE**: Some of the fk alterations deletes some rows in relation tables, this needs to be addressed to see which keys are conflicting before anything is put into production. EVERYTHING IS FLUID and can be EASILY changed.

The frontend is written in [Reactjs](https://reactjs.org/) using the [Nextjs](https://nextjs.org/) framework. Nextjs was chosen for the easy routing model and for server-side rendering possibilities. The existing U.I is located in `/frontend/dacite` and is just a re-making of the php dacite u.i in react with perhaps a view extra editing functionalities.

## Getting started

There are two main things needed to get started developing this application:

1.  Docker must be installed
2.  A db dumb or a connection to the gunnison server, with a local forward of the db.

### Docker

This application leverages docker containers and docker-compose. To install docker go [here](https://www.docker.com/get-started). Once docker is installed, run `docker-compose up` to bring up the application, it may take some time the on initialization as it will need to pull images for postgres14, postgrest, and node. **NOTE** postgrest may fail and the frontend won't show anything because there is no database!

The frontend docker container is configured for development with quick reload that would normally be seen in a nextjs app. This is done by a simple dockerfile that's entry command is `npm run dev` and then mounting the local directory to a volume within the docker container. This means theres no need to deal with a local npm environment!

### Database

The database in this application is an ever-evolving subset of the `burwell.macrostrat` database.schema on the `gunnison` server. In the same postgres cluster there is a database called `column_data` which is a copy of the database with these alterations and can be used to run this application.

You can run scripts without password prompts if you set the PGPASSWORD for gunnison in a .env file in the directory of the project.

**IF** (you have a local_forward for gunnison set up)

In `/database/bin` you will find a script called `dump-burwell` that is designed to get the schema and data of a subset of the db tables on gunnison.macrostrat and apply the alterations and views. From the root directory run `database/bin/dump-burwell -h` to view the flag options and their defaults. Unless you have changed the docker-compose container names, then the only option that matters is `-p` the port of the gunnison db. The defualt port is `54381`, but if you had the db configured to `5432` the command would be `database/bin/dump-burwell -p 5432`. **NOTE**: In order for this to work, you need to be running the application (`docker-compose up`).

**ELSE**

1. Dump the `column_data` database from the gunnison postgres cluster to a [pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html) file.
2. Get that file to your local computer.
3. Restore that pg_dump into the postgres docker container using [pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html).

```
docker-compose exec -T db pg_restore -v -U postgres -d column_data > $$dump_file$$
```
