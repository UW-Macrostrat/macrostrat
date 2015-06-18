#! /bin/bash

python scripts/update_unit_boundaries.py && python scripts/build_lookup_unit_intervals.py && python scripts/build_lookup_strat_names.py && python scripts/build_lookup_unit_liths_api.py && python scripts/build_pbdb_matches.py
