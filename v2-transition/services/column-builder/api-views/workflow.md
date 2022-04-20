# API View workflow

This application uses [Postgrest](https://postgrest.org/en/stable/) to autogenerate a RestAPI from a specific schema of a database. Postgrest is implemented through it's official docker-image as can be seen in the `docker-compose.yaml` file.

Here, you'll also see that `PGRST_DB_SCHEMA` is set to `macrostrat_api`. This is implementing [schema isolation](https://postgrest.org/en/stable/schema_structure.html) such that postgrest only has access to one schema in the database. This allows us to implement strict security and authorization as well as create unique [views](https://www.postgresql.org/docs/current/sql-createview.html) as database queries to get customized views of the data. The core views for this application can be found in `01-views.sql` file in this folder. Many of them are recreations of the table exactly, however many are custom views of the data that were made specifically for pages on the frontend.

## Make new views

During development it may be necesary to quickly iterate on new data views and this project's architecture supports that. To quickly make a new data view, you can add a new sql file to this directory or add new sql to an existing file and then run `make create-fixtures` at the root of this project.

**NOTE**: This will run the sql files on the database again, there may be some errors if a VIEW already exists, etc. This script also reloads the postgrest-shcema, which **_needs_** to happen if views are changed or new ones are created.
