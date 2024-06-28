// A file mirroring this structure should be placed at /code/credentials.js
// in the Docker container.

exports.mysql = {
  host     : 'old-db.development.svc.macrostrat.org',
  user     : 'user',
  password : 'e7HQsRutOVpQqJWGcqAipgpn88SwLTJB',
  database : 'macrostrat',
  port     : '3306'
}

exports.pg = {
  host     : 'db.development.svc.macrostrat.org',
  port     : '5432',
  user     : 'macrostrat-admin',
  password : '*@I/TW.-kSY5M,l[o4@9AuU}'
}

exports.postgresDatabases = {
  burwell: 'burwell',
  geomacro: 'geomacro',
}


// This is the default Redis port
// NOTE: Redis is not configured at the moment
exports.redis = {
  port: 6379
}

// Generate a hash by running: node -e "console.log(require('uuid/v4')())"
exports.cacheRefreshKey = 'put-hash-here'
