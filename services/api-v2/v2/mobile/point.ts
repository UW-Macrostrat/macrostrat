'use strict'

var api = require("../api"),
    async = require("async"),
    larkin = require("../larkin");

var _ = require("underscore")

var priorities = {
  'tiny': ['tiny', 'small', 'medium', 'large'],
  'small': ['small', 'medium', 'large', 'tiny'],
  'medium': ['medium', 'large', 'small', 'tiny'],
  'large': ['large', 'medium', 'small', 'tiny']
}

function buildSQL(scale, where) {
  return `
    (
      SELECT
      m.map_id,
      m.source_id,
      COALESCE(m.name, '') AS name,
      COALESCE(m.age, '') AS age,
      COALESCE(m.strat_name, '') AS strat_name,
      COALESCE(m.lith, '') AS lith,
      COALESCE(m.descrip, '') AS descrip,
      COALESCE(m.comments, '') AS comments,
      array_agg(DISTINCT liths.lith) AS liths_full,
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
      LEFT JOIN maps.map_liths ON map_liths.map_id = m.map_id
      LEFT JOIN macrostrat.liths ON map_liths.lith_id = liths.id
      ${where}
      GROUP BY m.map_id
    )
  `
}

module.exports = function(req, res, next) {
  if (!req.query.lat || !req.query.lng) {
    return larkin.info(req, res, next)
  }

  async.parallel({
    burwell: function(callback) {
      let where = [`
      ST_Intersects(m.geom, ST_GeomFromText($1, 4326))
      `]
      let params = [ `SRID=4326;POINT(${req.query.lng} ${req.query.lat})` ]

      where = ' WHERE ' + where.join(' AND ')

      var scaleSQL = Object.keys(priorities).map(function(scale) {
        return buildSQL(scale, where);
      }).join(' UNION ');

      var toRun = `SELECT * FROM ( ${scaleSQL} ) doit`;

      larkin.queryPg("burwell", toRun, params, function(error, result) {
        if (error || !result.rows || !result.rows.length) {
          return callback(null, {})
        }

        var currentScale = "large"
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
         })[0]
         callback(null, bestFit)
      })
    },

    // Query Macrostrat for polygon
    column: function(callback) {
      require('../columns')(req, null, null, (error, result) => {
        if (error) return callback(error)

        if (!result || !result.length) return callback(null, null)

        callback(null, result[0].col_id)
      })
    }

  }, function(error, result) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      var response = {
        "uid": result.burwell.map_id || "",
        "rocktype": result.burwell.liths_full || [],
        "age": result.burwell.age || "",
        "name": result.burwell.name || "",
        "desc": result.burwell.descrip || "",
        "comm": result.burwell.comments || "",
        "strat_unit": result.burwell.strat_name || "",
        "map_ref": result.burwell.ref || {},
        "col_id": result.column || "",
      };

      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
        compact: true
      }, {
        data: response
      });
    }
  });
}
