
exports.pg = {
  host: process.env.host,
  port: process.env.port,
  user: process.env.user,
  password: process.env.password,
  database: process.env.database
};


exports.postgresDatabases = {
  burwell: "macrostrat",
  geomacro: "geomacro",
  elevation: "elevation",
};

// This is the default Redis port
// NOTE: Redis is not configured at the moment
exports.redis = {
  port: 6379,
};

// Generate a hash by running: node -e "console.log(require('uuid/v4')())"
// NOTE: this is outdated and may not be used
exports.cacheRefreshKey = "put-hash-here";


/*
exports.macrostratDatabaseUrl = process.env.MACROSTRAT_DATABASE_URL;
exports.elevationDatabaseUrl = process.env.ELEVATION_DATABASE_URL;
exports.cacheRefreshKey = process.env.CACHE_REFRESH_KEY;
 */
