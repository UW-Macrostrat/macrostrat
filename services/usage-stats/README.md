# Usage Stats

This worker parses the Matomo database and post subsetted logs to the usage_stats schema for **Rockd** and **Macrostrat**

## Requirements

- Python 3.7+
- Packages listed in `requirements.txt`

## Local installation

   ```bash
   make install
   ```

## Running
Running the worker reads data from the Matomo database and writes the parsed logs to the `usage_stats.macrostrat_stats` and `usage_stats.rockd_stats` tables in the Macrostrat database

You can either run the app directly using

   ```bash
   make app
   ```

Or via docker using
   
   ```bash
   make docker
   ```