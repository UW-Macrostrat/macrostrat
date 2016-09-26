var api = require('../api')
var async = require('async')
var larkin = require('../larkin')
var _ = require('underscore')

var scaleLookup = {
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
var priorities = {
  'tiny': ['tiny', 'small', 'medium', 'large'],
  'small': ['small', 'medium', 'large', 'tiny'],
  'medium': ['medium', 'large', 'small', 'tiny'],
  'large': ['large', 'medium', 'small', 'tiny']
}

function summarizeUnits(units, callback) {
  callback({
    ids: units.map(function(d) { return d.unit_id }),
    strat_names: _.uniq(units.map(function(d) { return d.strat_name_long })).join(', '),
    rank_names: _.uniq(units.map(function(d) { return d.strat_name_long })).join(', '),
    max_thick: _.reduce(units.map(function(d) { return d.max_thick}), function(a, b) { return a + b}, 0),
    max_min_thick: _.reduce(units.map(function(d) {
      if (d.min_thick === 0) {
        return d.max_thick
      } else {
        return d.min_thick
      }
    }) , function(a, b) { return a + b}, 0),
    min_min_thick: _.reduce(units.map(function(d) { return d.min_thick}) , function(a, b) { return a + b}, 0),

    b_age: _.max(units, function(d) { return d.b_age }).b_age,
    t_age: _.min(units, function(d) { return d.t_age }).t_age,
    b_int_name: _.max(units, function(d) { return d.b_age }).b_int_name,
    t_int_name: _.min(units, function(d) { return d.t_age }).t_int_name,

    pbdb_collections: _.reduce(units.map(function(d) { return d.pbdb_collections }), function(a, b) { return a + b}, 0),
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
      COALESCE(mm.lith_ids, '{}') AS liths,
      m.t_interval AS t_int_id,
      ti.age_top::float AS t_int_age,
      ti.interval_name AS t_int_name,
      m.b_interval AS b_int_id,
      tb.age_bottom::float AS b_int_age,
      tb.interval_name AS b_int_name,
      mm.color,
      '${scale}' AS scale,
      (SELECT row_to_json(r) FROM (SELECT
        source_id,
        name,
        COALESCE(url, '') url,
        COALESCE(ref_title, '') ref_title,
        COALESCE(authors, '') authors,
        COALESCE(ref_year, '') ref_year,
        COALESCE(ref_source, '') ref_source,
        COALESCE(isbn_doi, '') isbn_doi
        FROM maps.sources
        WHERE source_id = m.source_id) r)::jsonb AS ref
      FROM maps.${scale} m
      LEFT JOIN macrostrat.intervals ti ON m.t_interval = ti.id
      LEFT JOIN macrostrat.intervals tb ON m.b_interval = tb.id
      LEFT JOIN lookup_${scale} mm ON mm.map_id = m.map_id
      ${where}
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

  async.parallel({
    elevation: function(cb) {
      require('../elevation')(req, null, null, function(error, data) {
        cb(null, data || {})
      })
    },
    burwell: function(cb) {
      var where = []
      var params = []
      where.push('ST_Intersects(m.geom, ST_GeomFromText($' + (where.length + 1) + ', 4326))');
      params.push(`SRID=4326;POINT(${req.query.lng} ${req.query.lat})`);

      // If no valid parameters passed, return an Error
      if (where.length < 1 && !('sample' in req.query)) {
        return cb('No valid parameters passed')
      }

      where = ' WHERE ' + where.join(' AND ')

      var scaleSQL = Object.keys(priorities).map(function(scale) {
        return buildSQL(scale, where);
      }).join(' UNION ');

      var toRun = `SELECT * FROM ( ${scaleSQL} ) doit`;
      larkin.queryPg('burwell', toRun, params, function(error, result) {
        if (error) {
          return cb(error)
        } else {

          var currentScale = scaleLookup[req.query.z]
          var returnedScales = _.uniq(result.rows.map(function(d) { return d.scale }))

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

           var bestFit = result.rows.filter(function(d) {
             if (targetScales.indexOf(d.scale) > -1) {
               delete d.scale
               return d
             }
           })

           // Add reference here! (or maybe in buildSQL...)

           var macroUnits = [].concat.apply([], bestFit.map(function(unit) { return unit.macro_units }))

           if (macroUnits.length) {
             require('../units')({query: { unit_id: macroUnits.join(',') } }, null, null, function(error, result) {
               if (error) console.log('Error fetching units', error);
               if (result && result.length) {
                 // summarizeUnits
                 summarizeUnits(result, function(summary) {
                   cb(null, {
                     burwell: bestFit,
                     macrostrat: summary
                   })
                 })
               } else {
                 cb(null, {
                   burwell: bestFit,
                   macrostrat: {}
                 })
               }
             })
           } else {
             cb(null, {
               burwell: bestFit,
               macrostrat: {}
             })
           }
        }
      })
    }
  }, function(error, data) {
    if (error) return larkin.error(req, res, next, error || null)

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
    }, {
      data: {
        elevation: data.elevation,
        burwell: data.burwell.burwell,
        macrostrat: data.burwell.macrostrat
      }
    })
  })
}
