#!/usr/bin/env bash -e


q="SELECT * FROM macrostrat_api.gbdb_strata_with_age_model"
macrostrat db psql -c "COPY ($q) TO STDOUT WITH CSV DELIMITER ',' HEADER" > gbdb-strata-with-linear-age-model-v2.csv
