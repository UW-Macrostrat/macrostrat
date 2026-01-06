#!/usr/bin/env bash

cat "$ROOT_DIR/geological_strata.csv" \
| macrostrat db psql -c 'COPY macrostrat_gbdb.strata FROM STDIN WITH (FORMAT CSV, HEADER true, FORCE_NULL (unit_thickness))'
