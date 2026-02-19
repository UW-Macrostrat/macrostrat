#!/usr/bin/env bash -e

root_dir=$ROOT_DIR

macrostrat db psql -c "TRUNCATE TABLE macrostrat_gbdb.chinalex"
cat "$root_dir/2024-08-18_chinalex.csv" \
| macrostrat db psql -c "COPY macrostrat_gbdb.chinalex FROM STDIN WITH (FORMAT CSV, HEADER true)"

macrostrat db psql -c "TRUNCATE TABLE macrostrat_gbdb.stratigraphic_dictionary_llm"
cat "$root_dir/stratigraphic-dictionary-llm-extraction.csv" \
| macrostrat db psql -c 'COPY macrostrat_gbdb.stratigraphic_dictionary_llm FROM STDIN WITH (FORMAT CSV, HEADER true)'
