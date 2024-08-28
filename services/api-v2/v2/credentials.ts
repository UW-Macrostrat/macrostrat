exports.pg = {
  connectionString: process.env.MACROSTRAT_DATABASE,
};

exports.postgresDatabases = {
  burwell: "macrostrat",
  geomacro: "geomacro"
};

// This is the default Redis port
// NOTE: Redis is not configured at the moment
exports.redis = {
  port: 6379,
};

// Generate a hash by running: node -e "console.log(require('uuid/v4')())"
// NOTE: this is outdated and may not be used
exports.cacheRefreshKey = "put-hash-here";
