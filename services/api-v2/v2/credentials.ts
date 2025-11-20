// Set up debug mode if needed
const pg = require("pg");

exports.debug = process.env.NODE_ENV === "development";
if (exports.debug) {
  // eslint-disable-next-line no-console
  console.log("Debug mode enabled");
}

// Keep old TLS handling for now
if (process.env.NODE_TLS_REJECT_UNAUTHORIZED == null) {
  process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
}

if (
  process.env.MACROSTRAT_DB_URL != null &&
  process.env.MACROSTRAT_DATABASE == null
) {
  console.warn(
    "Using deprecated database configuration, please migrate to the MACROSTRAT_DATABASE=<url> format",
  );
  process.env.MACROSTRAT_DATABASE = process.env.MACROSTRAT_DB_URL;
}

if (process.env.MACROSTRAT_DATABASE != null) {
  // Connect using a database URL
  const macrostratDatabaseURL = process.env.MACROSTRAT_DATABASE;

  // Get port from the main database URL
  const uri = new URL(macrostratDatabaseURL);

  const port = uri.port || "5432";
  const database = uri.pathname.substring(1);
  const dbString = `${port}/${database}`;

  const elevationDatabaseURL =
    process.env.ELEVATION_DATABASE ??
    macrostratDatabaseURL.replace(dbString, port + "/elevation");
  const aliceDatabaseURL =
    process.env.ALICE_DATABASE ??
    macrostratDatabaseURL.replace(dbString, port + "/alice");
  const rockdDatabaseURL =
    process.env.ROCKD_DATABASE ??
    macrostratDatabaseURL.replace(dbString, port + "/rockd");
  const whosOnFirstDatabaseURL =
    process.env.WHOS_ON_FIRST_DATABASE ??
    macrostratDatabaseURL.replace(dbString, port + "/whos_on_first");
  exports.pg = {
    macrostratDatabaseURL,
    elevationDatabaseURL,
    aliceDatabaseURL,
    rockdDatabaseURL,
    whosOnFirstDatabaseURL,
  };

  console.log(exports.pg);
}
//added exports.pg to https://github.com/UW-Macrostrat/tiger-macrostrat-config/blob/main/manifests/development/dev-web-stack/credentials.js
else {
  console.warn(
    "Using deprecated database configuration, please migrate to the MACROSTRAT_DATABASE=<url> format",
  );
  exports.pg = {
    host: process.env.host,
    port: process.env.port,
    user: process.env.user,
    password: process.env.password,
    database: "macrostrat",
  };
}

exports.postgresDatabases = {
  // "Burwell" used to be Macrostrat's map database, but it is now in the same database as the rest of Macrostrat
  burwell: "macrostrat",
  // The "geomacro" database is also now merged with Macrostrat
  geomacro: "macrostrat",
  elevation: "elevation",
  alice: "alice",
  rockd: "rockd",
  wof: "whos_on_first",
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
