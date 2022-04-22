# Stratigraphic Column Data Infrastructure

## About

This application aims to be the next step in data aquistion for stratigraphic columns in macrostrat. The approach taken here is PostgreSQL db centered, the exposed restful api is postgrest, which exists in the application as a docker container (see `docker-compose.yaml`).

The database is an evolution of the current postgres instance of macrostrat from the gunnison server. In `/database/db-alterations`, you can see several sql files that contain alterations run on the gunnison database to enhance the schema to fully unleash the power of postgresql, this includes things like explicit foreign keys.

The `postgrest` api is built on-top of the `macrostrat_api` schema in the database. This schema is a collection of views built off of the actual data. This approach nicely isolates the core data, in `macrostrat` schema, and the public facing views. This will also help with access control and authentication. A list of all custom views can be found in `/database/fixtures/views.sql`. **NOTE**: Some of the fk alterations deletes some rows in relation tables, this needs to be addressed to see which keys are conflicting before anything is put into production. EVERYTHING IS FLUID and can be EASILY changed.

The frontend is written in [Reactjs](https://reactjs.org/) using the [Nextjs](https://nextjs.org/) framework. Nextjs was chosen for the easy routing model and for server-side rendering possibilities. The existing U.I is located in `/dacite` and is just a re-making of the php dacite u.i in react with perhaps a view extra editing functionalities.

## Getting started

There are two main things needed to get started developing this application:

1.  Docker must be installed
2.  A db dump or a connection to the gunnison server, with a local forward of the db.

### Docker

This application leverages docker containers and docker-compose. To install docker go [here](https://www.docker.com/get-started). Once docker is installed, run `docker-compose up` to bring up the application, it may take some time the on initialization as it will need to pull images for postgres14, postgrest, and node. **NOTE** postgrest may fail and the frontend won't show anything because there is no database!

The frontend application is available through the `dacite` container in docker-compose. It is configured to reflect live code updates through local mounted volumes. However, you can also easily run the frontend outside of docker while running the database and postgrest API in docker. This functionality is encapsulated in environment variables, docker profiles, and a Makefile.

### Env variables, docker profiles, and make commands

To view the necesary env variables needed to run the application see the `env.example` in both the root project directory as well as the `dacite` directory. Many of these are set to defaults, however the ones for passwords and s3 buckets are obviously not real! If you copy and paste the others the application should work as designed.

This application uses docker profiles to enable quick local development of the frontend, `dacite`, outside of docker. By default `docker-compose up` will run every container except the s3 backup service. This is accomplished similary with `make start`. To run just the backend services in docker and the frontend locally, you can use the `make local_dev` command **OR** change the `COMPOSE_PROFILES` in the `.env` to only `dev`. It is reccommended to use `make local_dev` so you can leave the default variables in place.

### Frontend

To access the frontend, go to the `dacite` directory and run

```
npm install
npm run dev
```

This will bring up the development server for NextJS which includes hot-reload. NextJS abstracts the need for page routing by handling it all for us. Any file in the `pages` directory will be available via the browser at that path (i.e file `projects.ts` can be found at `/projects`). This application also makes use of dynamic routing using `[slugs]` to pass primary id's through the url. Not only does this allow for easy data fetching for each page, but also illuminates relationships between the pages (i.e `units/4/edit` is the editing page for unit #4). For more information view the [official docs](https://nextjs.org/docs/routing/dynamic-routes).

### Database

The database in this application is an ever-evolving subset of the `burwell.macrostrat` database.schema on the `gunnison` server. In the same postgres cluster there is a database called `column_data` which is a copy of the database with these alterations and can be used to run this application.

You can run scripts without password prompts if you set the PGPASSWORD for gunnison in a .env file in the directory of the project.

**IF** (you have a local_forward for gunnison set up)

In `/database/bin` you will find a script called `dump-burwell` that is designed to get the schema and data of the `column_data` db on gunnison and apply the alterations and views. From the root directory run `database/bin/dump-burwell -h` to view the flag options and their defaults. Unless you have changed the docker-compose container names, then the only option that matters is `-p` the port of the gunnison db on your local device (i.e a local forward). The defualt port is `54381`, but if you had the db configured to `5432` the command would be `database/bin/dump-burwell -p 5432`. **NOTE**: In order for this to work, you need to be running the application (`docker-compose up`).

**ELSE**

1. Dump the `column_data` database from the gunnison postgres cluster to a [pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html) file.
2. Get that file to your local computer.
3. Restore that pg_dump into the postgres docker container using [pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html).

```
docker-compose exec -T db pg_restore -v -U postgres -d column_data > $$dump_file$$
```

### Remote Database (beta)

The `postgrest` container takes the `PGRST_DB_URI` env variable to configure a database connection. If you didn't want to have a local postgres instance, you could configure this variable to reference the database on Gunnison. This may change in the future if an authentication system is enabled, we will have to pass a specific restricted user to this URI.
