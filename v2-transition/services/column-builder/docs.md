So far I've installed a postgis/postgres instance in a docker container for my column_data db.

I've also installed the db_backup service from uw-macrostrat.

I've modified a script from gunnison, bin/dump-burwell, that dumps the macrostrat schema
from the postgres instance of burwell from gunnison through a local forward.
This script begins by deleting and replacing my local database and then continues with the dump.

Troubles I had:

- I didn't have `pv` installed so the scrip wasn't working at first.
- The gunnison postgres/postgis debian image is 14.1 whereas my local postgres was at 13.5. I got an error about verision differences between pg_dump and pg_restore. I had to run some updates and change my path with the postgres app for mac.
