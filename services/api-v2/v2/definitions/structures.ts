var api = require("../api");
var larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var where = [];
  var params = {};
  var limit = req.query.hasOwnProperty("sample") ? "LIMIT 5" : "";

  if (req.query.structure_class) {
    where.push("structure_class IN (:structure_class)");
    params["structure_class"] = larkin.parseMultipleStrings(
      req.query.structure_class,
    );
  } else if (req.query.structure_type) {
    where.push("structure_type IN (:structure_type)");
    params["structure_type"] = larkin.parseMultipleStrings(
      req.query.structure_type,
    );
  } else if (req.query.structure) {
    where.push("structure IN (:structure)");
    params["structure"] = larkin.parseMultipleStrings(req.query.structure);
  } else if (req.query.structure_id) {
    where.push("structures.id IN (:structure_id)");
    params["structure_id"] = larkin.parseMultipleIds(req.query.structure_id);
  } else if (req.query.structure_like) {
    where.push("structure LIKE :structure");
    params["structure"] = "%" + req.query.structure_like + "%";
  }

  where = where.length ? "WHERE " + where.join(" AND ") : "";

  larkin.query(
    `
    SELECT
      structures.id AS structure_id,
      structure AS name,
      structure_type AS structure_type,
      COALESCE(structure_group, '') AS 'group',
      structure_class AS class
    FROM structures
    ${where}
    GROUP BY structures.id
    ${limit}
  `,
    params,
    function (error, data) {
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
    },
  );
};
