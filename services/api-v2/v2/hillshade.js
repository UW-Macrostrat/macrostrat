'use strict'
const api = require('./api')
const larkin = require('./larkin')
const buffer = require('@turf/buffer')
const envelope = require('@turf/envelope')
const hillshade = require('hillshadejs')

module.exports = (req, res, next) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  if ((!req.query.lat || !req.query.lng) && !('sample' in req.query)) {
    return larkin.error(req, res, next, 'Invalid parameters', 401)
  }

  let lng = larkin.normalizeLng(req.query.lng) || -89.4
  let lat = parseFloat(req.query.lat) || 43.07


  let point = {
    "type": "Point",
    "coordinates": [lng, lat]
  }

  let bigBuffer = envelope(buffer(point, 4, 'miles'))
  let smallBuffer = envelope(buffer(point, 2, 'miles'))

  let minLats = smallBuffer.geometry.coordinates[0].map(coords => {
    return coords[1]
  })

  let minLat = Math.min.apply(null, minLats)
  let maxLat = Math.max.apply(null, minLats)

  let maxLngs = bigBuffer.geometry.coordinates[0].map(coords => {
    return coords[0]
  })

  let minMaxLng = Math.min.apply(null, maxLngs)
  let maxMaxLng = Math.max.apply(null, maxLngs)

  let extent = [ minMaxLng, minLat, maxMaxLng, maxLat ]

  hillshade(extent, {
    zoom: 12,
    format: 'jpeg'
  }, (error, jpeg) => {
    if (error) {
      return larkin.error(req, res, next, 'Internal error', 500)
    }
    larkin.sendImage(req, res, next, jpeg)
  })
}
