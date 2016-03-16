exports.mysql = {
  host     : 'localhost',
  user     : 'user',
  password : 'password',
  database : 'playground',
  socketPath: '/tmp/mysql.sock'
//  socketPath: '/var/tmp/mariadb.sock'
}

exports.pg = {
  host     : 'localhost',
  port     : '5432',
  user     : 'postgres',
  password : ''
}

exports.redis = {
  port: 6379
}

exports.tiles = {
  configPath: '/path/to/config/compiled_styles',
  stashPath: '/path/to/root/tiles/burwell',
  path: '/path/to/tiles/burwell',
  config: '/path/to/burwell_large.xml',
  layers: ['vanilla', 'emphasized', 'lithologies', 'structures'],
  activeLayers: ['vanilla', 'emphasized']
}
