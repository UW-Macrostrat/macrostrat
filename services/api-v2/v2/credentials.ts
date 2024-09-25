if (process.env.MACROSTRAT_DB_URL != null && process.env.MACROSTRAT_DATABASE == null) {
  console.warn("Using deprecated database configuration, please migrate to the MACROSTRAT_DATABASE=<url> format");
  process.env.MACROSTRAT_DATABASE = process.env.MACROSTRAT_DB_URL;
}

if (process.env.MACROSTRAT_DATABASE != null) {
  // Connect using a database URL
  const macrostratDatabaseURL = process.env.MACROSTRAT_DATABASE
  const elevationDatabaseURL = process.env.ELEVATION_DATABASE ?? macrostratDatabaseURL.replace("5432/macrostrat", "5432/elevation");
  exports.pg = {
    macrostratDatabaseURL,
    elevationDatabaseURL
  };
} else {
  console.warn("Using deprecated database configuration, please migrate to the MACROSTRAT_DATABASE=<url> format");
  exports.pg = {
    host: process.env.host,
    port: process.env.port,
    user: process.env.user,
    password: process.env.password,
    database: process.env.database
  };
}


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
