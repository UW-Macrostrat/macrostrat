exports.mysql = {
  host     : 'localhost',
  user     : 'user',
  password : 'password',
  database : 'playground',
  socketPath: '/tmp/mysql.sock'
//  socketPath: '/var/tmp/mariadb.sock'
};
exports.pg = {
  host     : 'localhost',
  port     : '5432',
  user     : 'postgres',
  password : '',
  database : 'alice'
};
exports.tiles = {
  path: '/path/to/tiles/burwell',
  config: '/path/to/burwell_large.xml'
};
