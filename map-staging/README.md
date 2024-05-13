# macrostrat-map-staging

Scripts for bulk ingest of maps into Macrostrat


## CriticalMAAS

The map ingestion code written for TA4 tasks at the 6-month hackathon has
been re-packaged into the following commands of the Macrostrat CLI:

* `macrostrat maps ingest-file`
* `macrostrat maps ingest-from-csv`

See [../map-integration](../map-integration) for the implementation of these commands.


## Basic Setup and Configuration

1. Install [Poetry](https://python-poetry.org/).

2. Set the Python 3.11+ installation:

       poetry env use /usr/bin/python3.11

3. Install dependencies:

       poetry install --sync

4. Copy [`macrostrat.toml.template`](macrostrat.toml.template) to
   `macrostrat.toml`, copy the `example` section, and set each key to an
   appropriate value.


## CLI-based Bulk Ingest of Maps

The import process can be divided into two phases:

1. Scraping some data source for potential maps of interest. This is a task
   that cannot be generalized across multiple data sources.

2. Using the data obtained in the previous step to populate data into
   Macrostrat's database and object store. This task can be generalized to
   work across multiple data sources.

The scripts in the [`macrostrat.map_staging`](macrostrat/map_staging)
package address the first of these two steps. Each script outputs a CSV file
that can be fed into `macrostrat maps ingest-from-csv`, which addresses the
second of these two steps.


## Examples

Each example below describes how to scrape a data source and produce a CSV
file for the `macrostrat maps ingest-file` command.


### CriticalMAAS 9 Month Hackathon

The input CSV file here was provided by the CriticalMAAS program.

    poetry run python3 macrostrat/map_staging/criticalmaas_09.py data/criticalmaas_09_all.csv

The resulting output is in [data/criticalmaas_09.csv](data/criticalmaas_09.csv).

When running `macrostrat maps ingest-from-csv`, the `--filter ta1` option
can be used to attempt to exclude bounding boxes and map legends.


### National Geologic Map Database

The input CSV file here was provided by the USGS and flags NGMDB products of
interest to the CriticalMAAS program.

    poetry run python3 macrostrat/map_staging/ngmdb.py data/ngmdb_usgs_records_all.csv

The resulting output is in [data/ngmdb.csv](data/ngmdb.csv).


### Alaska Division of Geological & Geophysical Surveys

    poetry run python3 macrostrat/map_staging/alaska.py

The resulting output is in [data/alaska_all.csv](data/alaska_all.csv).
Several of these maps pose problems for Macrostrat's ingestion pipeline.
Deleting the corresponding rows yields [data/alaska.csv](data/alaska.csv).

When running `macrostrat maps ingest-from-csv`, the `--filter alaska` option
can be used to attempt to parse additional metadata from the files contained
in each archive.


### Nevada Bureau of Mines and Geology

    poetry run python3 macrostrat/map_staging/nevada.py

The resulting output is in [data/nevada.csv](data/nevada.csv).
