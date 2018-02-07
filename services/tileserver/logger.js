'use strict'

const pgHelper = require('@macrostrat/pg-helper')
const credentials = require('./credentials')

let pg = new pgHelper({
  user: credentials.pg_user,
  host: credentials.pg_host,
  port: credentials.pg_port,
  database: 'tileserver'
})


// Factory for querying PostGIS
function queryPg(sql, params, callback) {
  pool.connect((err, client, done) => {
    if (err) return callback(err)
    client.query(sql, params, (err, result) => {
      done()
      if (err) return callback(err)
      callback(null, result)
    })
  })
}

module.exports = () => {
  return {
    name: 'logger',
    init: (server, callback) => {
      callback()
    },
    reshook: (server, tile, req, res, result, callback) => {
      // Let the rest happen in the background
      callback()

      let app = ''
      let version = ''

      try {
        app = req.query.referrer
        version = req.query.version
      } catch(e) {
        // Don't care 💁
      }

      pg.query(`
        INSERT INTO requests (uri, layer, ext, x, y, z, referrer, app, app_version, cache_hit, redis_hit)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      `, [
        req._parsedUrl.pathname,
        tile.layer,
        tile.filename.replace('*.', '').replace('t.', ''),
        tile.x,
        tile.y,
        tile.z,
        req.headers['referer'] || '',
        app,
        version,
        (res._headers['x-tilestrata-cachehit'] || false),
        (res._headers['x-tilestrata-redishit'] || false)
      ], (error) => {
        if (error) {
          console.log(error)
        }
      })
    }
  }
}

/*
CREATE TABLE requests (
  req_id serial NOT NULL PRIMARY KEY,
  uri text,
  layer text,
  ext text,
  x integer,
  y integer,
  z integer,
  referrer text,
  app text,
  app_version text,
  cache_hit boolean default false,
  redis_hit boolean default false,
  time timestamp without time zone default now()
);
*/
