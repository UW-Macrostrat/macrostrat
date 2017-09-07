'use strict'

const fs = require('fs')
const path = require('path')
const cover = require('@mapbox/tile-cover')
const async = require('async')
const pg = require('pg')
const ProgressBar = require('progress')
const st = require('geojson-bounds')
const request = require('request')
const credentials = require('credentials')

const tileserver = require('./server')

tileserver.port = 5454
tileserver.start()

const minZooms = {
  'carto': 0,
  'tiny': 0,
  'small': 2,
  'medium': 4,
  'large': 9
}

const zooms = [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ]
const cachedZooms = [ 11, 12, 13 ]
const layers = [ 'carto', 'tiny', 'small', 'medium', 'large']

const pool = new pg.Pool({
  user: credentials.pg_user,
  host: credentials.pg_host,
  port: credentials.pg_port,
  database: 'burwell'
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

function getTile(tile, callback) {
  let tasks = []

  Object.keys(minZooms).forEach(layer => {
    if (tile.z >= minZooms[layer]) {
      tasks.push(function(cb) {
        request({
          url: `http://localhost:5454/${layer}/${tile.z}/${tile.x}/${tile.y}.${tile.extension}`,
          headers: {
            'X-Tilestrata-SkipCache': '*'
          }
        }, (error, response, body) => {
          if (error || response.statusCode != 200) return cb(error || 'Bad request')
          cb(null)
        })
      })
    }
  })

  async.parallel(tasks, (error) => {
    if (error) return callback(error)
    callback(null)
  })
}

function deleteTile(tile, callback) {
  let tasks = []

  Object.keys(minZooms).forEach(layer => {
    if (tile.z >= minZooms[layer]) {
      tasks.push(function(cb) {
        request({
          url: `http://localhost:5454/${layer}/${tile.z}/${tile.x}/${tile.y}.${tile.extension}`,
          headers: {
            'X-Tilestrata-DeleteTile': credentials.secret
          }
        }, (error, response, body) => {
          if (error || response.statusCode != 200) return cb(error || 'Bad request')
          cb(null)
        })
      })
    }
  })

  async.parallel(tasks, (error) => {
    if (error) return callback(error)
    callback(null)
  })
}

// Given [minLng, minLat] and [maxLng, maxLat] generate a GeoJSON polygon
function polygonFromMinMax(min, max) {
  return {
    "type": "Polygon",
    "coordinates": [[
      min,
      [min[0], max[1]],
      max,
      [max[0], min[1]],
      min
    ]]
  }
}

// Wrapper for tile-cover
function getTileList(geom, z) {
  return cover.tiles(geom, { min_zoom: z, max_zoom: z })
}

// Create the tiles
function seed(layer, tiles, callback) {
  let bar = new ProgressBar('     :bar :current of :total', { total: tiles.length, width: 50 })

  // Create 20 tiles at a time
  async.eachLimit(tiles, 5, (tile, cb) => {
    getTile({
      z: tile[2],
      x: tile[0],
      y: tile[1],
      extension: 'png',
      layer: layer
    }, (error) => {
      bar.tick()
      setImmediate(cb)
    })
  }, () => {
    callback(null)
  })
}

function remove(layer, tiles, callback) {
  let bar = new ProgressBar('     :bar :current of :total', { total: tiles.length, width: 50 })

  // Delete 20 tiles at a time
  async.eachLimit(tiles, 20, (tile, cb) => {
    deleteTile({
      z: tile[2],
      x: tile[0],
      y: tile[1],
      extension: 'png',
      layer: layer
    }, (error) => {
      bar.tick()
      setImmediate(cb)
    })
  }, () => {
    callback(null)
  })
}

function reseed(source_id) {
  if (!source_id) {
    console.log('Please provide a source_id')
    process.exit(1)
  }
  async.waterfall([
    (callback) => {
      // Chop it at 85N and 85S to keep tile-cover happy
      queryPg(`
        SELECT ST_AsGeoJSON(
          ST_Intersection(
            ST_GeomFromText('POLYGON ((-179 -85, -179 85, 179 85, 179 -85, -179 -85))', 4326),
            ST_SetSRID(rgeom, 4326)
          )
        ) AS geometry
        FROM maps.sources
        WHERE source_id = $1
      `, [ source_id ], (error, result) => {
        if (error) return callback(error)
        if (!result || !result.rows || !result.rows.length) return callback('No geometry found')

        callback(null, JSON.parse(result.rows[0].geometry))
      })
    },

    // If the scale is medium or large, clear the cache
    (shapes, callback) => {
      console.log('   ** Clearing large cache **')
      async.eachSeries(cachedZooms, (z, cba) => {
        console.log(`     z${z}`)
        remove('carto', getTileList(shapes, z), (error) => {
          setImmediate(cba)
        })
      }, () => {
        callback(null, shapes)
      })
    },

    // Seed the cache
    (shapes, callback) => {
      console.log('   ** Seeding **');
      let tiles = {}
      let tileIdx = {}

      async.eachLimit(zooms, 1, (z, zcallback) => {
        tiles[z] = []

        let shapeTiles = getTileList(shapes, z)
        for (let j = 0; j < shapeTiles.length; j++) {
          if (!tileIdx[shapeTiles[j].join('|')]) {
            tileIdx[shapeTiles[j].join('|')] = true
            tiles[z].push(shapeTiles[j])
          }
        }

        console.log(`     z${z}`)
        seed('carto', tiles[z], () => {
          zcallback()
        })
      }, (error) => {
        callback(error)
      })
    }
  ], (error) => {
    // Close connection pool to postgres
    pool.end()
    if (error) {
      console.log(error)
      process.exit(1)
    }
    console.log('Done seeding')
    process.exit()
  })
}


reseed(process.argv[2])
