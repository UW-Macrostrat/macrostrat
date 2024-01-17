exports.mysql = {
  host     : 'localhost',
  user     : 'user',
  password : 'password',
  database : 'macrostrat',
  socketPath: '/tmp/mysql.sock'
//  socketPath: '/var/tmp/mariadb.sock'
}

exports.pg = {
  host     : 'localhost',
  port     : '5432',
  user     : 'postgres',
  password : ''
}

// This is the default Redis port
exports.redis = {
  port: 6379
}

// Generate a hash by running: node -e "console.log(require('uuid/v4')())"
exports.cacheRefreshKey = 'put-hash-here'
