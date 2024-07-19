exports.mysql = {
  host: 'mariadb',
  user: 'root',
  password: 'supersmash',
  database: 'macrostrat',
  port: '3306'
  //  socketPath: '/var/tmp/mariadb.sock'
};

exports.pg = {
  host: 'postgres',
  port: '5432',
  user: 'postgres',
  password: 'moovitbro'
};

exports.redis = {
  port: 6379
};

exports.cacheRefreshKey = 'put-hash-here';