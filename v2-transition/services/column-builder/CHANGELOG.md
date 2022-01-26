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
