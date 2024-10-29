if (process.env.MACROSTRAT_DB_URL != null && process.env.MACROSTRAT_DATABASE == null) {
  console.warn("Using deprecated database configuration, please migrate to the MACROSTRAT_DATABASE=<url> format");
  process.env.MACROSTRAT_DATABASE = process.env.MACROSTRAT_DB_URL;
}

if (process.env.MACROSTRAT_DATABASE != null) {
  // Connect using a database URL
  const macrostratDatabaseURL = process.env.MACROSTRAT_DATABASE
  const elevationDatabaseURL = process.env.ELEVATION_DATABASE ?? macrostratDatabaseURL.replace("5432/macrostrat", "5432/elevation");
  const aliceDatabaseURL = process.env.ALICE_DATABASE ?? macrostratDatabaseURL.replace("5432/macrostrat", "5432/alice");
  const rockdDatabaseURL = process.env.ROCKD_DATABASE ?? macrostratDatabaseURL.replace("5432/macrostrat", "5432/rockd");
  exports.pg = {
    macrostratDatabaseURL,
    elevationDatabaseURL,
    aliceDatabaseURL,
    rockdDatabaseURL
  };
}
//added exports.pg to https://github.com/UW-Macrostrat/tiger-macrostrat-config/blob/main/manifests/development/dev-web-stack/credentials.js
else {
  console.warn("Using deprecated database configuration, please migrate to the MACROSTRAT_DATABASE=<url> format");
exports.pg = {
  host: process.env.host,
  port: process.env.port,
  user: process.env.user,
  password: process.env.password,
  database: 'macrostrat'
};
}


exports.postgresDatabases = {
  burwell: "macrostrat",
  geomacro: "geomacro",
  elevation: "elevation",
  alice: "alice",
  rockd: "rockd"
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
