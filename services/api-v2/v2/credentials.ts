const {
  mysql,
  pg,
  redis,
  cacheRefreshKey,
  postgresDatabases = {},
  elevationDatabase,
} = require("../credentials.ts");

exports.mysql = mysql;

exports.pg = pg;
// This is the default Redis port
exports.redis = redis;
// Generate a hash by running: node -e "console.log(require('uuid/v4')())"
exports.cacheRefreshKey = cacheRefreshKey;

exports.postgresDatabases = postgresDatabases;

exports.elevationDatabase = elevationDatabase;
