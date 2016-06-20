var api = require("./api")
var dbgeo = require("dbgeo")
var larkin = require("./larkin")


module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var where = []
  var params = []
  var limit = ''

  var validParams = {
    'measurement': 'measurements.measurement',
    'measurement_type': 'measurements.measurement_type',
    'measurement_class': 'measurements.measurement_class',
    'measurement_id': 'measurements.id',
    'measure_id': 'measures.id',
    'measuremeta_id': 'measuremeta.id',
    'lith_id': 'measuremeta.lith_id'
  }

  Object.keys(req.query).forEach(function(param) {
    if (validParams.hasOwnProperty(param)) {
      where.push(validParams[param] + ' IN ($' + (where.length + 1) + ')')

      if (param.substr(param.length - 3, param.length) === '_id') {
        params.push(larkin.parseMultipleIds(req.query[param]))
      } else {
        params.push(larkin.parseMultipleStrings(req.query[param]))
      }
    }
  })

  if (where.length) {
    where = 'WHERE ' + where.join(' AND ')
  } else {
    where = ''
  }

  if (req.query.hasOwnProperty('sample')) {
    limit = 'LIMIT 10'
  }

  larkin.query(`
    SELECT
      measurements.id AS measurement_id,
      measures.id AS measure_id,
      measurement,
      measurement_class,
      measurement_type,
      method,
      units,
      measure_value,
      v_error,
      COALESCE(v_error_units, '') v_error_units,
      v_type,
      v_n,
      lat,
      lng,
      sample_geo_unit,
      sample_lith,
      lith_id,
      sample_descrip,
      ref_id,
      GROUP_CONCAT(COALESCE(unit_id, '')) AS units
    FROM measures
    JOIN measurements ON measures.measurement_id = measurements.id
    JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
    LEFT JOIN unit_measures ON unit_measures.measuremeta_id = measuremeta.id
    ${where}
    GROUP BY measures.id
    ${limit}
  `, params, function(error, response) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      for (var i = 0; i < response.length; i++) {
        response[i].units = response[i].units.split(',').map(function(d) {
          return parseInt(d)
        })
      }

      if ((req.query.format && api.acceptedFormats.geo[req.query.format])) {
        dbgeo.parse({
          "data": response,
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "geometryType": "ll",
          "geometryColumn": ["lat", "lng"]
        }, function(error, result) {
          if (error) return larkin.error(req, res, next, error)

          larkin.sendData(req, res, next, {
            format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
            bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
            refs: 'ref_id'
          }, {
            data: result
          })
        })
      } else {
        larkin.sendData(req, res, next, {
          format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
          bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
          refs: 'ref_id'
        }, {
          data: response
        })
      }
    }
  })
}
