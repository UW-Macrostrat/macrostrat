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
      COALESCE(mm.lith_ids, '{}') AS liths,
      array((SELECT lith FROM macrostrat.liths WHERE id =  ANY(lith_ids))) AS liths_full,
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

module.exports = function(req, res, next) {
  if (req.query.lat && req.query.lng) {
    async.parallel({
      burwell: function(callback) {
        var where = []
        var params = []
        where.push('ST_Intersects(m.geom, ST_GeomFromText($' + (where.length + 1) + ', 4326))');
        params.push(`SRID=4326;POINT(${req.query.lng} ${req.query.lat})`);

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
        larkin.queryPg("geomacro", "SELECT id AS col_id FROM macrostrat.cols WHERE ST_Contains(poly_geom, ST_GeomFromText($1, 4326)) and status_code='active'", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
            if (error) {
              callback(error);
            } else {
              if (result.rows.length === 1) {
                callback(null, result.rows[0]);
              } else {
                larkin.queryPg("geomacro", "SELECT id AS col_id FROM macrostrat.cols WHERE ST_Intersects(poly_geom, ST_Buffer(ST_GeomFromText($1, 4326), 1)) and status_code='active' ORDER BY ST_Distance(ST_GeomFromText($1, 4326), poly_geom) LIMIT 1", ["POINT(" + req.query.lng + " " + req.query.lat + ")"], function(error, result) {
                  if (error) {
                    callback(error);

                  // If no columns are found within 1 degree, return an empty result
                  } else if (result.rows.length < 1) {
                    callback(null, {});
                  } else {
                  // Otherwise return the closest one
                    callback(null, { "col_id": result.rows[0].col_id });
                  }
                });
              }
            }
          });
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
          "col_id": (result.column && result.column.col_id) ? result.column.col_id : ""
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

  } else {
    larkin.info(req, res, next);
  }
}
