const api = require('../api')
const larkin = require('../larkin')
const https = require('https')
const async = require('async')

module.exports = (req, res, next) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  let categories = [
    'column',
    'econ',
    'environ',
    'group',
    'interval',
    'lith_att',
    'lithology',
    'mineral',
    'project',
    'strat_name',
    'structure',
    'places'
  ]


  let foundCategories = []

  if (req.query.include) {
    let includes = req.query.include.split(',')
    for (let i = 0; i < includes.length; i++) {
      if (categories.indexOf(includes[i]) > -1) {
        foundCategories.push(includes[i])
      }
    }

  } else if (req.query.exclude) {
    let excludes = req.query.exclude.split(',')
    for (let j = 0; j < categories.length; j++) {
      if (excludes.indexOf(categories[j]) < 0) {
        foundCategories.push(categories[j])
      }
    }
  } else {
    foundCategories = categories
  }
  // if ((Object.keys(req.query).indexOf('query') == -1) || (Object.keys(req.query).indexOf('sample') == -1)) {
  //   return larkin.info(req, res, next)
  // }

  async.parallel({
    places: (callback) => {
      https.get(`https://api.mapbox.com/geocoding/v5/mapbox.places/${req.query.query}.json?access_token=pk.eyJ1IjoiamN6YXBsZXdza2kiLCJhIjoiY2pjMjBiYWRjMDh2ZzJ4cHIwMjdyeWpieCJ9.EO2U9fSUuSPFvJ8LBQ4QSg&types=country,region,locality,place,poi.landmark`, res => {
        res.setEncoding('utf8')
        let body = ''
        res.on('data', data => {
          body += data
        })
        res.on('end', () => {
          body = JSON.parse(body)
          callback(null, body.features.map(place => {
            return {
              type: 'place',
              category: 'place',
              place_type: (place.place_type && place.place_type.length) ? place.place_type[0] : '',
              name: place.place_name,
              bbox: place.bbox || [],
              center: place.center || []
            }
          }))
        })
      })
    },
    macrostrat: (callback) => {
      larkin.queryPg('burwell', `
        SELECT id, name, type, category
        FROM macrostrat.autocomplete
        WHERE name ILIKE $1
          AND category = ANY($2)
        LIMIT 100
      `, [`${req.query.query}%`, foundCategories], (error, result) => {
        if (error) {
          return callback(error)
        }
        callback(null, result.rows)
      })
    }
  }, (error, results) => {
    if (error) {
      console.log(error)
      return larkin.error(req, res, next, error)
    }

    larkin.sendData(req, res, next, {
      format: 'json',
      compact: true
    }, {
      data: results.macrostrat.concat(results.places)
    })
  })
}
