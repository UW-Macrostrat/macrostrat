# Rockd Usage Stats

The project is meant to parse Traefik logs and post to rockd api, in order to store location statistics for rockd

## Requirements

- Python 3.7+
- Packages listed in `requirements.txt`

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/davidsklar99/rockd-usage-stats.git
   cd rockd-usage-stats

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
