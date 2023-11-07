#! /usr/local/bin/node

var inquirer = require('inquirer')
var pg = require('pg')
var async = require('async')
var mkdirp = require('mkdirp')
var exec = require('child_process').exec;
var yaml = require('yamljs')
var credentials = yaml.load('../credentials.yml')

if (credentials.pg_passwd) {
  credentials.pg_passwd = ':' + credentials.pg_passwd
}
// Factory for querying Postgres
function queryPg(db, sql, params, callback) {
  pg.connect(`postgres://${credentials.pg_user}@${credentials.pg_host}/${db}`, function(err, client, done) {
    if (err) return callback(err)
    var query = client.query(sql, params, function(err, result) {
      done()
      if (err) return callback(err)
      callback(null, result)
    })
  })
}

inquirer.prompt([{
  type: 'list',
  name: 'etype',
  message: 'Would you like to import, export, or remove a source?',
  choices: ['import', 'export', 'remove']
}, {
  type: 'list',
  name: 'db',
  message: 'Which database would you like to import INTO?',
  choices: ['burwell-staging', 'burwell'],
  when: function(answers) {
    return answers.etype === 'import'
  }
}, {
  type: 'list',
  name: 'db',
  message: 'Which database would you like to export from?',
  choices: ['burwell-staging', 'burwell'],
  when: function(answers) {
    return answers.etype === 'export'
  }
}, {
  type: 'list',
  name: 'db',
  message: 'Which database would you like to delete from?',
  choices: ['burwell-staging', 'burwell'],
  when: function(answers) {
    return answers.etype === 'remove'
  }
}, {
  type: 'input',
  name: 'source_id',
  message: 'Which source_id?'
}, {
  type: 'input',
  name: 'source_path',
  message: 'Please specify a path to the directory that contains the dump files',
  when: function(answers) {
    return answers.etype === 'import'
  }
}]).then(function(answers) {
  switch (answers.etype) {
    case 'export':
      exportSource(answers.db, answers.source_id)
      break
    case 'import':
      importSource(answers.db, answers.source_id, answers.source_path)
      break
    case 'remove':
      deleteSource(answers.db, answers.source_id)
      break
    default:
      console.log('huh?')
      process.exit(1)
  }
})

function deleteSource(db, source_id) {
  exportSource(db, source_id, function() {
    queryPg(db, 'SELECT source_id, name, primary_table, primary_line_table, scale FROM maps.sources WHERE source_id = $1', [source_id], function(error, result) {
      if (error) {
        console.log(error)
        process.exit(1)
      }
      if (!result.rows || !result.rows.length) {
        console.log('This source id was not found')
        process.exit(1)
      }

      var meta = result.rows[0]

      async.parallel([
        function(callback) {
          queryPg(db, `DELETE FROM lookup_${meta.scale} WHERE map_id IN (SELECT DISTINCT map_id FROM maps.${meta.scale})`, [], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        },

        function(callback) {
          queryPg(db, `DELETE FROM maps.map_liths WHERE map_id IN (SELECT DISTINCT map_id FROM maps.${meta.scale})`, [], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        },

        function(callback) {
          queryPg(db, `DELETE FROM maps.map_strat_names WHERE map_id IN (SELECT DISTINCT map_id FROM maps.${meta.scale})`, [], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        },

        function(callback) {
          queryPg(db, `DELETE FROM maps.map_units WHERE map_id IN (SELECT DISTINCT map_id FROM maps.${meta.scale})`, [], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        },

        function(callback) {
          queryPg(db, `DROP TABLE sources.${meta.primary_table}`, [], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        },

        function(callback) {
          queryPg(db, `DELETE FROM maps.${meta.scale} WHERE source_id = $1`, [source_id], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        },

        function(callback) {
          queryPg(db, `DELETE FROM maps.sources WHERE source_id = $1`, [source_id], function(error) {
            if (error) return callback(error)
            callback(null)
          })
        }

      ], function(error) {
        if (error) {
          console.log(error)
          process.exit(1)
        }
        console.log(`Deleted source ${source_id} (${meta.name}) from ${db} and backed it up to ./${meta.name.replace(' ', '_')}`)
        process.exit(0)
      })
    })
  })
}

function importSource(db, source_id, path) {

  // First make sure it doesn't already exist
  queryPg(db, 'SELECT source_id FROM maps.sources WHERE source_id = $1', [source_id], function(error, result) {
    if (error) {
      console.log(error)
      process.exit(1)
    }
    if (result.rows && result.rows.length) {
      console.log('This source is already in the database. Will not import.')
      process.exit(1)
    }

    var meta
    async.series([
      // By now we know it is legit, so start by importing the maps.sources table
      function(cb) {
        exec(`gunzip -c ${path}/sources.tsv.gz | psql -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} burwell-staging -c "COPY maps.sources FROM STDIN"`, function(error,stout, stderr) {
          if (error) {
            console.log(error)
          }
          cb()
        })
      },
      // Next, select that content out of the table
      function(cb) {
        queryPg(db, 'SELECT source_id, name, primary_table, primary_line_table, scale FROM maps.sources WHERE source_id = $1', [source_id], function(error, result) {
          if (error) {
            console.log(error)
            process.exit(1)
          }
          if (!result.rows || !result.rows.length) {
            console.log('Source ID not found')
            process.exit(1)
          }
          // Basic info about the source
          meta = result.rows[0]

          cb()
        })
      },
      function(cb) {
        var targetTables = {
          'maps.map_liths': buildImportCmd(db, path, 'map_liths', 'maps.map_liths'),
          'maps.map_strat_names': buildImportCmd(db, path, 'map_strat_names', 'maps.map_strat_names'),
          'maps.map_units': buildImportCmd(db, path, 'map_units', 'maps.map_units')
        }

        targetTables[`maps.${meta.scale}`] = buildImportCmd(db, path, `${meta.scale}`, `maps.${meta.scale}`)
        targetTables[`public.lookup_${meta.scale}`] = buildImportCmd(db, path, `lookup_${meta.scale}`, `public.lookup_${meta.scale}`)
        targetTables[`sources.${meta.primary_table}`] = `gunzip -c ${path}/${meta.primary_table}.sql.gz | psql -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} burwell-staging`
        if (meta.primary_line_table) {
          targetTables[`sources.${meta.primary_line_table}`] = `gunzip -c ${path}/${meta.primary_line_table}.sql.gz | psql -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} burwell-staging`
        }

        async.each(Object.keys(targetTables), function(table, cb) {
          exec(targetTables[table], function(error, stdout, stderr) {
            if (error) {
              console.log(error)
            }
            cb()
          })
        }, function(error) {

          console.log(`Imported ${meta.name} (${meta.source_id})`)
          process.exit(0)
        })
      }
    ], function(error) {
      if (error) {
        console.log(error)
        process.exit(1)
      }
    })
  })
}

function exportSource(db, source_id, callback) {
  // First get source metadata from maps.sources
  queryPg(db, 'SELECT source_id, name, primary_table, primary_line_table, scale FROM maps.sources WHERE source_id = $1', [source_id], function(error, result) {
    if (error) {
      console.log(error)
      process.exit(1)
    }
    if (!result.rows || !result.rows.length) {
      console.log('Source ID not found')
      process.exit(1)
    }
    // Basic info about the source
    var meta = result.rows[0]

    // Create a folder for the output, if it doesn't exist
    mkdirp.sync(__dirname + `/${meta.name.replace(' ', '_')}`)

    var targetTables = {
      'maps.sources': buildDumpStatement(db, meta, 'maps.sources', `
        SELECT source_id, name, primary_table, url, ref_title, authors, ref_year, ref_source, isbn_doi, scale, primary_line_table, licence, features, area, priority, rgeom
        FROM maps.sources
        WHERE source_id = ${meta.source_id}`),
      'maps.map_liths': buildDumpStatement(db, meta, 'maps.map_liths', `
        SELECT map_id, lith_id, basis_col
        FROM maps.map_liths
        WHERE map_id IN (
          SELECT DISTINCT map_id
          FROM maps.${meta.scale}
          WHERE source_id = ${meta.source_id}
        )`),
      'maps.map_strat_names': buildDumpStatement(db, meta, 'maps.map_strat_names', `
        SELECT map_id, strat_name_id, basis_col
        FROM maps.map_strat_names
        WHERE map_id IN (
          SELECT DISTINCT map_id
          FROM maps.${meta.scale}
          WHERE source_id = ${meta.source_id}
        )`),
      'maps.map_units': buildDumpStatement(db, meta, 'maps.map_units', `
        SELECT map_id, unit_id, basis_col
        FROM maps.map_units
        WHERE map_id IN (
          SELECT DISTINCT map_id
          FROM maps.${meta.scale}
          WHERE source_id = ${meta.source_id}
        )
      `)
    }

    targetTables[`maps.${meta.scale}`] =  buildDumpStatement(db, meta, `maps.${meta.scale}`, `
      SELECT map_id, orig_id, source_id, name, strat_name, age, lith, descrip, comments, t_interval, b_interval, geom
      FROM maps.${meta.scale}
      WHERE source_id = ${meta.source_id}
    `)
    targetTables[`public.lookup_${meta.scale}`] = buildDumpStatement(db, meta, `public.lookup_${meta.scale}`, `
      SELECT map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color
      FROM public.lookup_${meta.scale}
      WHERE map_id IN (
        SELECT DISTINCT map_id
        FROM maps.${meta.scale}
        WHERE source_id = ${meta.source_id}
      )
    `)
    targetTables[`sources.${meta.primary_table}`] = `pg_dump -c -O -x -t sources.${meta.primary_table} -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} burwell | gzip > ${meta.name.replace(' ', '_')}/${meta.primary_table}.sql.gz`

    if (meta.primary_line_table) {
      targetTables[`sources.${meta.primary_line_table}`] = `pg_dump -c -O -x -t sources.${meta.primary_line_table} -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} burwell | gzip > ${meta.name.replace(' ', '_')}/${meta.primary_line_table}.sql.gz`
    }

    async.each(Object.keys(targetTables), function(table, cb) {
      exec(targetTables[table], function(error, stdout, stderr) {
        if (error) {
          console.log(error)
        }
        cb()
      })
    }, function(error) {
      if (callback) {
        callback(null)
      } else {
        console.log(`Exported ${meta.name} (${meta.source_id}) to ./${meta.name.replace(' ', '_')}`)
        process.exit(0)
      }
    })
  })
}


function buildDumpStatement(db, meta, table, sql) {
  return `psql -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} ${db} -c 'COPY (${sql}) TO STDOUT' | gzip > ${meta.name.replace(' ', '_')}/${table.split('.')[1]}.tsv.gz`
}

function buildImportCmd(db, path, target_file, table) {
  return `gunzip -c ${path}/${target_file}.tsv.gz | psql -U ${credentials.pg_user} -h ${credentials.pg_host} -p ${credentials.pg_port} ${db} -c "COPY ${table} FROM STDIN"`
}
