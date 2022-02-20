const translate = require('google-translate-api')
const pg = require('pg')
const async = require('async')

const PG_USER = 'john'
const PG_HOST = 'localhost'
const PG_PORT = 5439
const PG_DB = 'burwell'

// Factory for querying PostGIS
function queryPg(sql, params, callback) {
  pg.connect(`postgres://${PG_USER}@${PG_HOST}:${PG_PORT}/${PG_DB}`, (err, client, done) => {
    if (err) return callback(err)

    client.query(sql, params, (err, result) => {
      done()
      if (err) return callback(err)
      callback(null, result);
    })
  })
}

//let fieldsToTranslate = ['descripcio', 'claslitoed']
let fieldsToTranslate = ['claslitoed']
let table = 'sources.catalunya50k'

async.waterfall([
  (done) => {
    queryPg(fieldsToTranslate.map(field => {
      return `
        ALTER TABLE ${table} DROP COLUMN IF EXISTS ${field}_en;
        ALTER TABLE ${table} ADD COLUMN ${field}_en text;
      `
    }).join(' '), [], (error) => {
      if (error) {
        console.log(error)
        process.exit(1)
      }
      console.log('Added English fields')
      done()
    })
  },

  (done) => {
    async.eachLimit(fieldsToTranslate, 1, (field, callback) => {
      queryPg(`
        SELECT DISTINCT ${field}
        FROM ${table}
      `, [], (error, results) => {
        if (error) {
          console.log(error)
          process.exit(1)
        }

        async.eachLimit(results.rows, 5, (d, doneTranslating) => {
          translate(d[field], {from: 'ca', to: 'en'}).then(res => {
            console.log(res.text)
            queryPg(`
              UPDATE ${table}
              SET ${field}_en = $1
              WHERE ${field} = $2
            `, [ res.text, d[field] ], (error) => {
              if (error) {
                console.log(error)
                process.exit(1)
              }
              doneTranslating()
            })
          }).catch(error => {
            console.log('could not translate', d, error)
            process.exit(1)
          })
        }, (error) => {
          callback()
        })
      })
    }, error => {
      done()
    })
  }
], (error) => {
  console.log('Done translating')
  process.exit(0)
})
