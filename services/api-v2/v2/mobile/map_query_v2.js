const api = require('../api')
const async = require('async')
const larkin = require('../larkin')
const _ = require('underscore')

const LINE_TOLERANCE  = 20

const scaleLookup = {
  0: 'tiny',
  1: 'tiny',
  2: 'tiny',
  3: 'small',
  4: 'small',
  5: 'small',
  6: 'medium',
  7: 'medium',
  8: 'medium',
  9: 'large',
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
      (
           SELECT json_agg(w) FROM (
               SELECT split_part(q, '|', 1)::int AS strat_name_id, split_part(q, '|', 2) AS rank_name
               FROM (
                  SELECT unnest(array_agg(DISTINCT concat(lookup_strat_names.strat_name_id, '|', lookup_strat_names.rank_name))) q
               ) foo
           ) w
      ) as strat_names,
      array_agg(DISTINCT units.id) AS unit_ids,
      COALESCE(sum(units.max_thick), 0)::int AS max_thick,
      COALESCE(sum(units.min_thick), 0)::int AS max_min_thick,
      COALESCE(sum(units.min_thick), 0)::int AS min_min_thick,
      max(lookup_units.b_age::numeric)::float AS b_age,
      min(lookup_units.t_age::numeric)::float AS t_age,
      sum(lookup_units.pbdb_collections)::int AS pbdb_collections,
      sum(lookup_units.pbdb_occurrences)::int AS pbdb_occs,
      (
        SELECT row_to_json(r) FROM (
          SELECT
            id AS int_id,
            interval_name AS int_name,
            interval_color AS color
          FROM macrostrat.intervals
          JOIN macrostrat.timescales_intervals ON timescales_intervals.interval_id = intervals.id
          WHERE age_bottom >= max(lookup_units.b_age::numeric) AND age_top <= max(lookup_units.b_age::numeric)
            AND timescale_id = 11
          ORDER BY age_bottom - age_top
          LIMIT 1
        ) r
      ) as b_int,
      (
        SELECT row_to_json(r) FROM (
          SELECT
            id AS int_id,
            interval_name AS int_name,
            interval_color AS color
          FROM macrostrat.intervals
          JOIN macrostrat.timescales_intervals ON timescales_intervals.interval_id = intervals.id
          WHERE age_bottom >= min(lookup_units.t_age::numeric) AND age_top <= min(lookup_units.t_age::numeric)
            AND timescale_id = 11
          ORDER BY age_bottom - age_top
          LIMIT 1
        ) r
      ) as t_int,
      (
        SELECT COALESCE(json_agg(t), '[]') FROM (
          SELECT lith_id, lith, lith_type, lith_class, lith_color AS color, lith_fill, round(count(comp_prop)/sum(count(comp_prop)) over(), 3) AS prop
          FROM macrostrat.unit_liths
          JOIN macrostrat.liths ON liths.id = unit_liths.lith_id
          WHERE unit_id = ANY(array_agg(units.id))
          GROUP BY lith_id, lith, lith_type, lith_class, lith_color, lith_fill
        ) t
      ) AS liths,
      (
        SELECT COALESCE(json_agg(t), '[]') FROM (
          SELECT DISTINCT econ_id, econ, econ_type, econ_class, econ_color AS color
          FROM macrostrat.unit_econs
          JOIN macrostrat.econs ON econs.id = unit_econs.econ_id
          WHERE unit_id = ANY(array_agg(units.id))
        ) t
      ) AS econs,
      (
        SELECT COALESCE(json_agg(t), '[]') FROM (
          SELECT DISTINCT environ_id, environ, environ_type, environ_class, environ_color AS color
          FROM macrostrat.unit_environs
          JOIN macrostrat.environs ON environs.id = unit_environs.environ_id
          WHERE unit_id = ANY(array_agg(units.id))
        ) t
      ) AS environs
    FROM macrostrat.lookup_strat_names
    LEFT JOIN macrostrat.unit_strat_names ON unit_strat_names.strat_name_id = lookup_strat_names.strat_name_id
    LEFT JOIN macrostrat.units ON units.id = unit_strat_names.unit_id
    LEFT JOIN macrostrat.lookup_units ON units.id = lookup_units.unit_id
    LEFT JOIN macrostrat.units_sections ON units.id = units_sections.unit_id
    LEFT JOIN macrostrat.cols ON units_sections.col_id = cols.id
    WHERE ${params.unit_ids ? 'units.id' : 'lookup_strat_names.strat_name_id'} = ANY($1)
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

function buildSQL(scale, where) {
  return `
    (SELECT
      m.map_id,
      m.source_id,
      COALESCE(m.name, '') AS name,
      COALESCE(m.age, '') AS age,
      COALESCE(m.strat_name, '') AS strat_name,
      COALESCE(m.lith, '') AS lith,
      COALESCE(m.descrip, '') AS descrip,
      COALESCE(m.comments, '') AS comments,
      COALESCE(mm.unit_ids, '{}') AS macro_units,
      COALESCE(mm.strat_name_ids, '{}') AS strat_names,
      COALESCE((
        SELECT json_agg(t) FROM (
          SELECT id AS lith_id, lith, lith_type, lith_class, lith_color AS color, lith_fill
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
             mapPolygon.macrostrat = {}
             return done(null, mapPolygon)
           }
           delete mapPolygon.strat_names
           delete mapPolygon.macro_units
           getUnits(params, (error, units) => {
             if (error) {
               return cb(error)
             }
             if (units.length) {
               mapPolygon.macrostrat = units[0]
             } else if (params.strat_name_ids) {
               mapPolygon.macrostrat = {
                 strat_names: params.strat_name_ids
               }
             } else {
               mapPolygon.macrostrat = {}
             }

             done(null, mapPolygon)
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
