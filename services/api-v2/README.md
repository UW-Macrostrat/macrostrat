# Macrostrat API
The API for SCIENCE

## About
The Macrostrat API provides diverse macrostratigraphic and geologic data in a concise, queryable format.

## Prerequisites
#### Software
MariaDB, PostgreSQL, Nodejs, Python, and [Macrostrat CLI](https://github.com/UW-Macrostrat/utils) are required

#### Data
The following databases must be in place:  
+ MariaDB - macrostrat
+ Postgres - burwell, alice, wof, elevation

## Setup

First clone the repo:
````
git clone https://github.com/UW-Macrostrat/macrostrat-api.git
cd macrostrat-api
````

Next, install dependencies:
````
npm install
````

Depending on the permissions of the directory you might need to manually install dependencies for each version of the API as well:

````
cd v1 && npm install && cd .. && cd v2 && npm install && cd ..
````

Each of the two versions of the API has a credentials file that is not tracked by git. Start by copying the example files:
````
cp v1/credentials.example.js v1/credentials.js && cp v2/credentials.example.js v2/credentials.js
````

For `v1/credentials.js` fill in your MariaDB and PostgreSQL user information. Do the same for `v2/credentials.js`, but also update the port for Redis if necessary, and follow the inline instructions for generating a cache refresh key. The cache refresh key is used as a secret parameter to programmatically refresh the column cache, such as in situations in which the underlying data has been changed (editing, adding, etc).

## Running
To start the API simply run `node server.js` which will start a process on port 5000. To use a different port, you can specify it during startup as so: `node server.js 5151`.

For production use `pm2` is recommended. To start as a single process:
````
pm2 start server.js --name macrostrat-api
````

or, to start in a load balanced mode with two processes:
````
pm2 start server.js --name macrostrat-api -i 2
````


### Test
````
npm test
````

### Organization
Each version of the API functions as a self-contained module, and therefore has its own ````package.json```` and dependencies.

### Authors
[John J Czaplewski](https://github.com/jczaplew) and [Shanan E Peters](http://strata.geoglogy.wisc.edu)

### License
CC0 for all code unique to this API.
