#! /bin/bash

python scripts/import.py && echo "Done reloading boundaries into database" && python scripts/build_lookup_unit_intervals.py && python scripts/build_lookup_strat_names.py && python scripts/build_lookup_unit_liths.py && python scripts/build_pbdb_matches.py && python scripts/fix_zeros.py
