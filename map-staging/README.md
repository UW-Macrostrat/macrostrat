# macrostrat-map-staging

Scripts for staging maps into Macrostrat

> An earlier version of these scripts, including proof-of-concept scripts
> written for the CriticalMAAS 6-month Hackathon, can be found at
> [brianaydemir/macrostrat-map-ingestion](https://github.com/brianaydemir/macrostrat-map-ingestion).


## Basic Setup and Configuration

1. Install [Poetry](https://python-poetry.org/).

2. Tell Poetry which Python 3.11+ installation to use for this project's environment.

       poetry env use /usr/bin/python3.11

3. Install dependencies.

       poetry install --sync

4. Copy [`macrostrat.toml.template`](macrostrat.toml.template) to
   `macrostrat.toml`, copy the `example` section, and set each key to an
   appropriate value.


## CLI-based Bulk Ingest of Maps

The `macrostrat.map_ingestion` package was written to support bulk ingest
of maps using the `macrostrat maps run-pipeline` command.

See [UW-Macrostrat/macrostrat](https://github.com/UW-Macrostrat/macrostrat)
for the implementation of `run-pipeline`.

1. Scrape a data source by running

       poetry run python3 -m macrostrat.map_ingestion.scrapers.${SCRAPER_MODULE} > maps.csv

   Replace `${SCRAPER_MODULE}` with one of the modules in
   [macrostrat/map_ingestion/scrapers](macrostrat/map_ingestion/scrapers).

2. Process the maps listed in the CSV file produced by the previous step by
   running

       poetry run python3 -m macrostrat.map_ingestion.driver maps.csv
