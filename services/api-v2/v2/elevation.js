'use strict'
const api = require('./api')
const larkin = require('./larkin')
const https = require('https')
const polyline = require('@mapbox/polyline')
const credentials = require('./credentials')

module.exports = (req, res, next, cb) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  if ((req.query.lat && req.query.lng) || 'sample' in req.query) {
    let lat = req.query.lat || 43.07
    let lng = larkin.normalizeLng(req.query.lng) || -89.4

    https.get(`https://elevation.mapzen.com/height?json={"range":false,"shape":[{"lat":${lat},"lon":${lng}}]}&api_key=${credentials.mapzen_key}`, (response) => {
      let body = ''

      response.on('data', (chunk) => {
        body += chunk
      })
      response.on('end', () => {
        let mapzenResponse = JSON.parse(body)
        let toSend = [{ elevation: mapzenResponse.height[0] || null }]

        if (cb) return cb(null, toSend)
        larkin.sendData(req, res, next, {
          format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
          compact: true
        }, {
          data: toSend
        })
      })
    })

  } else if (req.query.start_lng && req.query.start_lat && req.query.end_lng && req.query.end_lat) {
    req.query.start_lng = larkin.normalizeLng(req.query.start_lng)
    req.query.end_lng = larkin.normalizeLng(req.query.end_lng)

    let leftLng = (req.query.start_lng < req.query.end_lng) ? req.query.start_lng : req.query.end_lng
    let leftLat = (req.query.start_lng < req.query.end_lng) ? req.query.start_lat : req.query.end_lat
    let rightLng = (req.query.start_lng < req.query.end_lng) ? req.query.end_lng : req.query.start_lng
    let rightLat = (req.query.start_lng < req.query.end_lng) ? req.query.end_lat : req.query.start_lat
    let linestring = `SRID=4326;LINESTRING(${leftLng} ${leftLat}, ${rightLng} ${rightLat})`
    let westPoint = `SRID=4326;POINT(${leftLng} ${leftLat})`

    larkin.queryPg('elevation', `
      WITH first AS (
        SELECT ST_SetSRID((ST_Dump(
        ST_LocateAlong(
          ST_AddMeasure(my_line, 0, 200), generate_series(0, 200)
        )
        )).geom, 4326) AS geom FROM (
          SELECT ST_GeomFromText($1) AS my_line
        ) q
      )

      SELECT
        ST_X(geom) AS lng,
        ST_Y(geom) AS lat,
        round((ST_Distance_Sphere(geom, $2) * 0.001)::numeric, 2)::float AS d
      FROM first
    `, [linestring, westPoint], (error, result) => {
      if (error) {
        if (cb) return cb(error)
        return larkin.error(req, res, next, 'Internal error', 500)
      }
      let pts = result.rows

      let encodedPolyline = polyline.encode(pts.map(pt => { return [pt.lat, pt.lng] }), 6)

      https.get(`https://elevation.mapzen.com/height?json={"range":true,"encoded_polyline":"${encodedPolyline}"}&api_key=${credentials.mapzen_key}`, (response) => {
        let body = ''

        response.on('data', (chunk) => {
          body += chunk
        })

        response.on('end', () => {
          let elevationResult = JSON.parse(body)

          if (cb) return cb(null, result.rows)
          larkin.sendData(req, res, next, {
            format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : 'json',
            compact: true
          }, {
            data: pts.map((pt, i) => {
              pt.elevation = elevationResult.range_height[i][1]
              return pt
            })
          })
        })
      })

    })
  } else {
    return larkin.error(req, res, next, 'Invalid Parameters', 401)
  }
}
