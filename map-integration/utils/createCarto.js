'use strict'
/*
@input
  - source_id
  - scale

+ Cut target source's footprint out of carto table

+ Create a new temp table to hold the intermediate product to speed up inserts

+ Get all polygons from the underlying scale that intersect the target source's footprint
  - Group by priority
    - Order by priority ASC
    - Cut a hole in the built up polygons equal to the group
    - Insert each group

+ Do the same for the target scale

+ Insert all from the temp table into the carto table

*/
const async = require('async')
const pg = require('pg')
const yaml = require('yamljs')
const path = require('path')
const credentials = yaml.load(path.join(__dirname, '..', 'credentials.yml'))

const UNDER = {
  'small': 'tiny',
  'medium': 'small',
  'large': 'medium'
}
const scaleIsIn = {
    tiny: ['tiny'],
    small: ['small', 'medium'],
    medium: ['medium', 'large'],
    large: ['large']
}

// Factory for querying PostGIS
function queryPg(sql, params, callback) {
  pg.connect(`postgres://${credentials.pg_user}@${credentials.pg_host}:${credentials.pg_port}/${credentials.pg_db}`, (err, client, done) => {
    if (err) return callback(err)

    client.query(sql, params, (err, result) => {
      done()
      if (err) return callback(err)
      callback(null, result)
    })
  })
}

const SCALES = ['tiny', 'small', 'medium', 'large']

const SCALE = process.argv[2]

if (SCALES.indexOf(SCALE) === -1) {
  console.log('Invalid scale')
  process.exit(1)
}

processScale(SCALE, (error) => {
  if (error) console.log(error)
  process.exit()
})

function processScale(the_scale, bedone) {
  let SCALE_UNDER = UNDER[the_scale]
  console.log(` ${the_scale}`)
  async.series([
    // Create a new temp table to hold the intermediate product to speed up inserts
    (callback) => {
      console.log('   1. Clean and create')
      queryPg(`
        DROP TABLE IF EXISTS carto_temp;
        CREATE TABLE carto_temp AS SELECT * FROM carto_new.${the_scale} LIMIT 0;
        CREATE INDEX ON carto_temp USING GiST (geom);
      `, [], (error) => {
        if (error) return callback(error)
        callback()
      })
    },

    /*
    + Get all polygons from the underlying scale that intersect the target source's footprint
      - Group by priority
        - Order by priority ASC
        - Cut a hole in the built up polygons equal to the group
        - Insert each group
    */
    (callback) => {
      console.log('   2. Scale under')
      if (!SCALE_UNDER) {
        return callback()
      }
      insertScale(SCALE_UNDER, (error) => {
        if (error) return callback(error)
        callback()
      })
    },

    // + Do the same for the target scale
    (callback) => {
      console.log('   3. Scale')
      insertScale(the_scale, (error) => {
        if (error) return callback(error)
        callback()
      })
    },
    (callback) => {
      console.log('   4. Delete')
      queryPg(`
        TRUNCATE TABLE carto_new.${the_scale};
      `, [], (error) => {
        if (error) return callback(error)
        callback()
      })
    },

    // Insert new geometries
    (callback) => {
      console.log('   5. Insert')
      queryPg(`
        INSERT INTO carto_new.${the_scale} (map_id, source_id, scale, geom)
        SELECT * FROM carto_temp;
      `, [], (error) => {
        if (error) return callback(error)
        callback()
      })
    },

    // Clean up the temp table
    (callback) => {
      console.log('   6. Clean up')
      queryPg(`
        DROP TABLE carto_temp;
      `, [], (error) => {
        if (error) return callback(error)
        callback()
      })
    },

    (callback) => {
      console.log('   7. Clean up bad geometries')
      queryPg(`
        DELETE FROM carto_new.${the_scale} WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
      `, [], (error) => {
        if (error) return callback(error)
        callback()
      })
    }

  ], (error) => {
    if (error) return bedone(error)
    bedone()
  })
}

function insertScale(scale, callback) {
  // Find the unique priorities of a given scale
  queryPg(`
    SELECT DISTINCT sa.new_priority
    FROM maps.${scale} x
    JOIN maps.sources sa ON x.source_id = sa.source_id
    ORDER BY new_priority ASC
  `, [ ], (error, result) => {
    if (error) return callback(error)

    async.eachLimit(result.rows, 1, (row, done) => {
      /*
        1. Chop out a spot for the geometries we will insert (cookie cutter)
        2. Remove empty geometries
        3. Insert new geometries
      */
      async.series([
        (cb) => {
          queryPg(`
            WITH first AS (
                SELECT COALESCE(ST_Union(x.rgeom), 'POLYGON EMPTY') AS geom
                FROM maps.sources x
                WHERE x.new_priority = $1 AND $2::text = ANY(x.display_scales)
            )
            UPDATE carto_temp
            SET geom = ST_Difference(carto_temp.geom, q.geom)
            FROM first q
            WHERE ST_Intersects(carto_temp.geom, q.geom);
          `, [ row.new_priority, scale ], (error) => {
            if (error) return cb(error)
            cb()
          })
        },

        (cb) => {
          queryPg(`
            DELETE FROM carto_temp WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
          `, [], (error) => {
            if (error) return cb(error)
            cb()
          })
        },

        (cb) => {
          queryPg(`
            INSERT INTO carto_temp
            SELECT
              m.map_id,
              m.source_id,
              '${scale}'::text AS scale,
              ST_SetSRID(m.geom, 4326) AS geom
            FROM maps.${scale} m
            JOIN maps.sources sa ON m.source_id = sa.source_id
            WHERE sa.new_priority = $1 AND $2::text = ANY(sa.display_scales);
          `, [ row.new_priority, scale ], (error) => {
            if (error) return cb(error)
            cb()
          })
        },

        (cb) => {
          queryPg(`
            DELETE FROM carto_temp WHERE geometrytype(geom) NOT IN ('POLYGON', 'MULTIPOLYGON');
          `, [ ], (error) => {
            if (error) return cb(error)
            cb()
          })
        }
      ], (error) => {
        if (error) return done(error)
        done()
      })
    }, (error) => {
      if (error) return callback(error)
      callback()
    })
  })
}
