var api = require("../api"),
  larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql =
    "SELECT minerals.id AS mineral_id, mineral AS mineral, min_type as mineral_type, formula AS formula, formula_tags AS formula_tags, url AS url, hardness_min AS hardness_min, hardness_max AS hardness_max, crystal_form AS crystal_form, color AS mineral_color, lustre AS lustre FROM minerals";

  var params = {};

  if (req.query.mineral_id) {
    sql += " WHERE minerals.id IN (:mineral_id)";
    params["mineral_id"] = larkin.parseMultipleIds(req.query.mineral_id);
  } else if (req.query.mineral) {
    sql += " WHERE mineral IN (:mineral)";
    params["mineral"] = larkin.parseMultipleStrings(req.query.mineral);
  } else if (req.query.mineral_type) {
    sql += " WHERE min_type IN (:mineral_type)";
    params["mineral_type"] = larkin.parseMultipleStrings(
      req.query.mineral_type,
    );
  } else if (req.query.element) {
    var parsedElements = larkin
      .parseMultipleStrings(req.query.element)
      .join("|");
    params = {
      elementA: ".*" + parsedElements + "[A-Z]+",
      elementB: ".*" + parsedElements + "[0-9]+",
      elementC: ".*" + parsedElements + "[\\(|\\),x,\\+,\\[,\\],-]",
      elementD: ".*" + parsedElements + "$",
    };

    sql +=
      " WHERE formula REGEXP BINARY :elementA OR formula REGEXP BINARY :elementB OR formula REGEXP BINARY :elementC OR formula REGEXP BINARY :elementD ORDER BY mineral";
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function (error, data) {
    if (error) {
      if (cb) {
        cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    }

    if (cb) {
      cb(null, data);
    } else {
      larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          bare: api.acceptedFormats.bare[req.query.format] ? true : false,
          compact: true,
        },
        {
          data: data,
        },
      );
    }
  });
};
