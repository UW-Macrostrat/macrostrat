#! /bin/bash
source scripts/credentials.py

mysql -u $mysql_user -p$mysql_passwd $mysql_db < scripts/redo_unit_boundaries.sql
echo "Done reloading boundaries into database"

python scripts/build_lookup_unit_intervals.py
python scripts/build_lookup_strat_names.py
python scripts/build_lookup_unit_liths.py
python scripts/build_pbdb_matches.py

python scripts/fix_zeros.py
