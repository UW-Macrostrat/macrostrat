const api = require('../api')
const async = require('async')
const larkin = require('../larkin')
const _ = require('underscore')

const LINE_TOLERANCE  = 20

const scaleLookup = {
  0: 'tiny',
  1: 'tiny',
  2: 'tiny',
  3: 'tiny',
  4: 'small',
  5: 'small',
  6: 'medium',
  7: 'medium',
  8: 'medium',
  9: 'medium',
  10: 'large',
  11: 'large',
  12: 'large',
  13: 'large',
  14: 'large',
  15: 'large',
  16: 'large',
  17: 'large',
  18: 'large',
  19: 'large',
  20: 'large',
  21: 'large',
  22: 'large',
  23: 'large',
  24: 'large'
}
// Determine a priority order for each scale
const priorities = {
  'tiny': ['tiny'],
  'small': ['small', 'tiny'],
  'medium': ['medium', 'small', 'tiny'],
  'large': ['large', 'medium', 'small', 'tiny']
}

// https://msdn.microsoft.com/en-us/library/bb259689.aspx
// Calcucate m/px given a latitude and a zoom level
function tolerance(lat, z) {
  return (Math.cos(lat * Math.PI/180) * 2 * Math.PI * 6378137) / (256 * Math.pow(2, z))
}

function getUnits(params, callback) {
  let p = (params.unit_ids) ? params.unit_ids : params.strat_name_ids
  larkin.queryPg('burwell', `
    SELECT
      units.id AS unit_id,
      unit_strat_names.strat_name_id,
      lookup_units.t_age::numeric,
      lookup_units.b_age::numeric,
      units.max_thick::numeric,
      units.min_thick::numeric,
      lookup_units.pbdb_collections,
      lookup_units.pbdb_occurrences,
      lookup_unit_attrs_api.lith,
      lookup_unit_attrs_api.environ,
      lookup_unit_attrs_api.econ,
      lookup_units.t_int_name,
      lookup_units.t_int_age,
      lookup_units.b_int_name,
      lookup_units.b_int_age,
      lookup_strat_names.rank_name AS strat_name_long
    FROM macrostrat.units
    JOIN macrostrat.lookup_unit_attrs_api ON lookup_unit_attrs_api.unit_id = units.id
    JOIN macrostrat.lookup_units ON units.id = lookup_units.unit_id
    LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.unit_id = units.id
    LEFT JOIN macrostrat.units_sections ON units.id = units_sections.unit_id
    LEFT JOIN macrostrat.cols ON units_sections.col_id = cols.id
    LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id = unit_strat_names.strat_name_id
    WHERE status_code = 'active'
      AND ${params.unit_ids ? 'units.id' : 'unit_strat_names.strat_name_id'} = ANY($1)
  `, [p], (error, result) => {
    if (error) return callback(error)
    callback(null, result.rows)
  })
}
function getBestFit(z, data) {
  var currentScale = scaleLookup[z]
  let returnedScales = [...new Set(result.map(d => { return d.scale }))]

  var targetScales = []

  // Iterate on possible scales given our z
  for (var i = 0; i < priorities[currentScale].length; i++) {
    // If that scale is present, record it
     if (returnedScales.indexOf(priorities[currentScale][i]) > -1) {
       targetScales.push(priorities[currentScale][i])
       if (currentScale != 'tiny' && currentScale != 'small') {
         break
       } else if (targetScales.length > 1) {
         break
       }
     }
   }

   var bestFit = data.filter(function(d) {
     if (targetScales.indexOf(d.scale) > -1) {
       delete d.scale
       return d
     }
   })

   return bestFit
}

function summarizeUnits(units, callback) {
  var stratNames = units.map(function(d) { return {
    name: d.strat_name_long,
    id: d.strat_name_id
  }})
  var recorded = {}
  var filteredStratNames = stratNames.filter(function(d) {
    if (!recorded[d.id]) {
      recorded[d.id] = d
      return d
    }
  })

  callback({
    unit_ids: units.map(function(d) { return d.unit_id }),
    strat_names: filteredStratNames,
    rank_names: [...new Set(units.map(d => { return d.strat_name_long }))].join(', '),
    max_thick: units.map(unit => { return unit.max_thick }).reduce((a, b) => { return parseFloat(a) + parseFloat(b) }, 0),
    max_min_thick: units.map(unit => {
      if (unit.min_thick === 0) {
        return unit.max_thick
      } else {
        return unit.min_thick
      }
    }).reduce((a, b) => { return parseFloat(a) + parseFloat(b) }, 0),
    min_min_thick: units.map(unit => { return unit.min_thick }).reduce((a, b) => { return parseFloat(a) + parseFloat(b) }, 0),

    b_age: units.map(unit => { return unit.b_age }).reduce((a, b) => {
      return Math.max(a, b)
    }),
    t_age: units.map(unit => { return unit.t_age }).reduce((a, b) => {
      return Math.min(a, b)
    }),

    b_int_name: _.max(units, function(d) { return d.b_age }).b_int_name,
    t_int_name: _.min(units, function(d) { return d.t_age }).t_int_name,

    pbdb_collections: units.map(unit => { return unit.pbdb_collections }).reduce((a, b) => { return a + b }, 0),
    lith: larkin.summarizeAttribute(units, 'lith'),
    environ: larkin.summarizeAttribute(units, 'environ'),
    econ: larkin.summarizeAttribute(units, 'econ'),
    uniqueIntervals: (function() {
      var min_age = 9999,
          min_age_interval = '',
          max_age = -1,
          max_age_interval = ''

      units.forEach(function(d, i) {
        if (d.t_age < min_age) {
          min_age = d.t_age
          min_age_interval = d.t_int_name
        }
        if (d.b_age > max_age) {
          max_age = d.b_age
          max_age_interval = d.b_int_name
        }
      })
      return (max_age_interval === min_age_interval) ? min_age_interval : max_age_interval + ' - ' + min_age_interval
    })()
  })
}


function buildSQL(scale, where) {
  return `
    (SELECT
      m.map_id,
      m.source_id,
      COALESCE(m.name, '') AS name,
      COALESCE(m.strat_name, '') AS strat_name,
      COALESCE(m.lith, '') AS lith,
      COALESCE(m.descrip, '') AS descrip,
      COALESCE(m.comments, '') AS comments,
      COALESCE(mm.unit_ids, '{}') AS macro_units,
      COALESCE(mm.strat_name_ids, '{}') AS strat_names,
      COALESCE((
        SELECT json_agg(t) FROM (
          SELECT id AS lith_id, lith, lith_type, lith_class, lith_color AS color
          FROM macrostrat.liths
          WHERE id = ANY(mm.lith_ids)
        ) t
      ), '[]') AS liths,
      (
        SELECT row_to_json(r) FROM (
          SELECT
            m.b_interval AS int_id,
            tb.age_bottom::float AS b_age,
            tb.age_top::float AS t_age,
            tb.interval_name AS int_name,
            tb.interval_color AS color
        ) r
      ) AS b_int,
      (
        SELECT row_to_json(r) FROM (
          SELECT
            m.t_interval AS int_id,
            ti.age_bottom::float AS b_age,
            ti.age_top::float AS t_age,
            ti.interval_name AS int_name,
            ti.interval_color AS color
        ) r
      ) AS t_int,
      mm.color,
      '${scale}' AS scale,
      (SELECT row_to_json(r) FROM (SELECT
        sources.name,
        sources.source_id,
        COALESCE(sources.url, '') url,
        COALESCE(sources.ref_title, '') ref_title,
        COALESCE(sources.authors, '') authors,
        COALESCE(sources.ref_year, '') ref_year,
        COALESCE(sources.ref_source, '') ref_source,
        COALESCE(sources.isbn_doi, '') isbn_doi) r)::jsonb AS ref
      FROM maps.${scale} m
      JOIN maps.sources ON m.source_id = sources.source_id
      LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id
      LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id
      LEFT JOIN lookup_${scale} mm ON mm.map_id = m.map_id
      ${where}
      ORDER BY sources.new_priority DESC
    )
  `
}

function buildLineSQL(scale) {
  return `
    (
      SELECT line_id, source_id, name, type, direction, descrip, scale, distance
      FROM (
          SELECT *, row_number() OVER (PARTITION BY source_id ORDER BY distance)
          FROM (
              SELECT
                m.line_id,
                m.source_id,
                COALESCE(m.name, '') AS name,
                COALESCE(m.new_type, '') AS type,
                COALESCE(m.new_direction, '') AS direction,
                COALESCE(m.descrip, '') AS descrip,
                '${scale}' AS scale,
                ST_Distance_Spheroid(m.geom, $1, 'SPHEROID["WGS 84",6378137,298.257223563]') AS distance
              FROM lines.${scale} m
              ORDER BY geom <-> $1
              LIMIT 10
          ) foo
          ORDER BY distance
      ) bar WHERE row_number = 1
    )
  `
}


// Accepts a longitude, a latitude, and a zoom level
// Returns the proper burwell data and macrostrat data
module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  if ((!req.query.lng || !req.query.lat || !req.query.z) && !req.query.hasOwnProperty('sample')) {
    return larkin.error(req, res, next, 'You are missing a required parameter', 400)
  }

  if ('sample' in req.query) {
    req.query.lng = -89.3
    req.query.lat = 43.03
    req.query.z = 10
  }

  req.query.lng = larkin.normalizeLng(req.query.lng)
  req.query.z = parseInt(req.query.z || 0)

  async.parallel({
    elevation: (cb) => {
      require('../elevation')(req, null, null, (error, data) => {
        if (data && data.length) {
          cb(null, data[0].elevation)
        } else {
          cb(null, null)
        }
      })
    },

    lines: (cb) => {

      var scaleSQL = Object.keys(priorities).map(scale => {
        return buildLineSQL(scale)
      }).join(' UNION ALL ')


      larkin.queryPg('burwell', `SELECT * FROM ( ${scaleSQL} ) doit`, [ `SRID=4326;POINT(${req.query.lng} ${req.query.lat})` ], (error, result) => {
        if (error) return cb(error)

        let currentScale = scaleLookup[req.query.z]
        let returnedScales = [...new Set(result.rows.map(row => { return row.scale }))]
        let targetScales = []

        // Iterate on possible scales given our z
        for (var i = 0; i < priorities[currentScale].length; i++) {
          // If that scale is present, record it
           if (returnedScales.indexOf(priorities[currentScale][i]) > -1) {
             targetScales.push(priorities[currentScale][i])
             if (currentScale != 'tiny' && currentScale != 'small') {
               break
             } else if (targetScales.length > 1) {
               break
             }
           }
         }

         // All the map polygons of the best appropriate scale
         let bestFits = result.rows.filter(d => {
           if (targetScales.indexOf(d.scale) > -1) {
             delete d.scale
             return d
           }
         })

         bestFits = bestFits.filter(line => {
           // Verify that the best fit is within a clickable tolerance
           if (line.hasOwnProperty('distance') && line.distance <= (tolerance(req.query.lat, req.query.z) * 20 )) {
             return line
           }
         }).map(line => {
           delete line.distance
           return line
         })

         cb(null, bestFits)
      })
    },
    burwell: function(cb) {

      let where = [`ST_Intersects(m.geom, ST_GeomFromText($1, 4326))`]
      let params = [`SRID=4326;POINT(${req.query.lng} ${req.query.lat})`]

      // If no valid parameters passed, return an Error
      if (where.length < 1 && !('sample' in req.query)) {
        return cb('No valid parameters passed')
      }

      where = ` WHERE ${where.join(' AND ')}`

      var scaleSQL = Object.keys(priorities).map(function(scale) {
        return buildSQL(scale, where);
      }).join(' UNION ALL ');

      var toRun = `SELECT * FROM ( ${scaleSQL} ) doit`;
      larkin.queryPg('burwell', toRun, params, (error, result) => {
        if (error) {
          return cb(error)
        }

        let currentScale = scaleLookup[req.query.z]
        let returnedScales = [...new Set(result.rows.map(row => { return row.scale }))]

        var targetScales = []

        // Iterate on possible scales given our z
        for (var i = 0; i < priorities[currentScale].length; i++) {
          // If that scale is present, record it
           if (returnedScales.indexOf(priorities[currentScale][i]) > -1) {
             targetScales.push(priorities[currentScale][i])
             if (currentScale != 'tiny' && currentScale != 'small') {
               break
             } else if (targetScales.length > 1) {
               break
             }
           }
         }

         // All the map polygons of the best appropriate scale
         var bestFit = result.rows.filter(d => {
           if (targetScales.indexOf(d.scale) > -1) {
             delete d.scale
             return d
           }
         })

         async.mapLimit(bestFit, 3, (mapPolygon, done) => {
           let params = {}
           if (mapPolygon.macro_units.length) {
             params = { 'unit_ids': mapPolygon.macro_units  }
           } else if (mapPolygon.strat_names.length) {
             params = { 'strat_name_ids': mapPolygon.strat_names }
           } else {
             return done(null, mapPolygon)
           }
           delete mapPolygon.strat_names
           delete mapPolygon.macro_units
           getUnits(params, (error, units) => {
             if (error) {
               return cb(error)
             }
             summarizeUnits(units, (summary) => {
               mapPolygon.macrostrat = summary
               done(null, mapPolygon)
             })
           })

           // done(null, mapPolygon)
         }, (error, results) => {
           if (error) return larkin.error(req, res, next, error)

           cb(null, results)
         })

      })
    }
  }, function(error, data) {
    if (error) return larkin.error(req, res, next, error || null)

    for (let i = 0; i < data.burwell.length; i++) {
      data.burwell[i].lines = []
      for (let j = 0; j < data.lines.length; j++) {
        if (data.burwell[i].source_id === data.lines[j].source_id) {
          data.burwell[i].lines.push(data.lines[j])
        }
      }
    }
    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
    }, {
      data: {
        elevation: data.elevation,
        mapData: data.burwell,
      }
    })
  })
}
