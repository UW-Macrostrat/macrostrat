# 01.06.22: Initial Commits

So far I've installed a postgis/postgres instance in a docker container for my column_data db.

I've also installed the db_backup service from uw-macrostrat.

I've modified a script from gunnison, bin/dump-burwell, that dumps the macrostrat schema
from the postgres instance of burwell from gunnison through a local forward.
This script begins by deleting and replacing my local database and then continues with the dump.

I've done a quick first pass looking at the tables in postgres:gunnison/macrostrat and added foreign keys and
run delete where statements in areas with non-matching key issues. I also took notes about how many rows were
removed from each. Most of the removed rows were in joining tables. All the sql used is in the `add-foreign-keys.sql` file.

The `dump-burwell` script has the option to run `add-foreign-keys` as well. This is a good place to start, we
can add on more scripts that alter the database into what we want and then add them to `dump-burwell`. Both scripts have flag options now as well with defaults.

Troubles I had:

- I didn't have `pv` installed so the scrip wasn't working at first.
- The gunnison postgres/postgis debian image is 14.1 whereas my local postgres was at 13.5. I got an error about verision differences between pg_dump and pg_restore. I had to run some updates and change my path with the postgres app for mac.

- There are 38,000 strat_names defined in units that are not in the strat_names table!!!

# 01.19.22: Pydantic, FastAPI, & Postgrest

I have added more database alterations including a procedure to update or create primary key sequences on
every primary key in the `macrostrat` schema.

I have created some Pydantic models for some of the major database modesl (Project, Column, Unit, etc). I also began creating a FastAPI with psycopg3 db bindings, however it quickly became apparent that the direction I was headed was creating a ORM, which for the purposes of this app, seemed overkill. The API doesn't need to handle much logic besides inserting and retrieving from the database.

To simplfy the application I have installed Postgrest to work as the API. I have created a few tests for Postgrest that include retrieving data (GET), creating new models (POST), and editing existing models (PATCH).
As well as linking two models via a foreign key insert into a joining table. These tests express the main functionality the application is meant to encompass.

The `dump-burwell` script has been updated to include the latest db-alterations.

# 01.25.22: PostGrest and Frontend

Introductory frontend with NextJs is created aiming to mimic current functionality of `Dacite`. More postgrest development with a separate DB schema `macrostrat_api`.

# 02.16.22: Frontend & Database

New pages for projects, column-groups, columns, units/sections and editors for each. Strat-Names also have an editor page which doesn't have db persistence yet. Other editors have persistence. Frontend needs some
code refactor to make things more organized and to eliminate repeated logic.

New views have been added and updated for postgrest access.

`macrostrat.strat_name` now has a `parent` column which is a key reference to `strat_name.id`. Might be an
easier way to construct the parent-child relationship for strat-name hierarchy. This is similar to how things were done in sparrow for sub-samples.

Strides have been made to design and implement database access control. The main drivers have been the auth tutorial on [postgrest](https://postgrest.org/en/stable/auth.html). The main id is to keep everythin db centered by creating base DB roles that have certain table level priveleges. And row-level priveleges can be tracked by assigning project or other data model ids to a specific web-user (stored in auth.users) who is mapped to a db role. Some introductory tests have been created but it is still very much a WORK IN PROGRESS.

# 04.20.22: Major Refactors

The backend python api has been removed as it is not necesary anymore. Frontend changes include, better page routing using dynamic slugs, database persistence working for all pages, except strat_name, and Increased loading speed using SSR. There are also several new helper functions for fetching data from the Postgrest API. I've moved as much data fetching as possible into the `getServerSideProps` function that enables SSR.

The `column_data` database is available on the `gunnison` server and is at this moment up-to-date with the current needs for this application.

A new script available through `make create-fixtures` allows for quickly updating the api-views and reloading the `postgrest-api` schema.

The frontend is no longer availble for development in Docker, there is a bug that I believe is related to SSR.

SQL for api-views are front and center now at the root of the application.
