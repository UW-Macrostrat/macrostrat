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

4. Copy [macrostrat.toml.template](macrostrat.toml.template) to
   `macrostrat.toml`, copy the `example` section to a new section named
   `development`, and set each key to an appropriate value.


## CLI-based Bulk Staging of Maps

The `macrostrat.map_staging` package was written to support bulk staging of
maps using the `macrostrat maps run-pipeline` command. (See
[../map-integration](../map-integration) for the implementation of
`run-pipeline`.)

1. Scrape a data source by running

       poetry run python3 -m macrostrat.map_staging.scrapers.${SCRAPER_MODULE} > maps.csv

   Replace `${SCRAPER_MODULE}` with one of the modules in
   [macrostrat/map_staging/scrapers](macrostrat/map_staging/scrapers).

   The CSV file produced by each of the scrapers contains columns
   corresponding to command-line arguments and options for `run-pipeline`.

2. Process the maps listed in the CSV file produced by the previous step by
   running

       poetry run python3 -m macrostrat.map_staging.driver maps.csv
