const api = require('../api')
const larkin = require('../larkin')

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

  larkin.queryPg('burwell', `
    SELECT id, name, type, category
    FROM macrostrat.autocomplete
    WHERE name ILIKE $1
      AND category = ANY($2)
    LIMIT 100
  `, [`${req.query.query}%`, foundCategories], (error, result) => {
    if (error) {
      console.log(error)
      return larkin.error(req, res, next, error)
    }

    larkin.sendData(req, res, next, {
      format: 'json',
      compact: true
    }, {
      data: result.rows
    })
  })
}
