# Usage Stats

The project is meant to parse the matomo database and post subsetted logs to the usage_stats schema

## Requirements

- Python 3.7+
- Packages listed in `requirements.txt`

## Installation


## Running
You can either run the script directly using 
   ```bash
   ./run.sh
   ```

Or you can use the docker container by running

   ```bash
   docker build -t stats .
   docker run --rm stats
   ```
