var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var where = "",
      params = {};

  if (req.query.hasOwnProperty("all")) {
    // do nothing
  } else if (req.query.col_id) {
    where = "WHERE s.col_id IN (:col_id)";
    params["col_id"] = larkin.parseMultipleIds(req.query.col_id);

  } else {
    return larkin.error(req, res, next, "An invalid parameter was passed");
  }

  larkin.query("SELECT s.id AS section_id, s.col_id, ints2.interval_name AS t_interval, min(t1_age) AS t_age, ints.interval_name AS b_interval, max(t1_age) AS b_age, count(u.id) AS units, COALESCE(r.fossils,0) AS pbdb_collections \
   FROM sections s \
    JOIN intervals ints on FO = ints.id \
    JOIN intervals ints2 on LO = ints2.id \
    JOIN units u ON u.section_id = s.id \
    LEFT JOIN ( \
        SELECT u.section_id, count(pbdb.id) as fossils FROM units u \
        JOIN pbdb_matches pbdb on pbdb.unit_id = u.id \
        GROUP BY u.section_id \
    ) r ON r.section_id = s.id \
    JOIN unit_boundaries ub ON s.id = ub.section_id \
   " + where +    
  " GROUP BY s.id", params, function(error, result) {
    if (error) {
      larkin.error(req, res, next, "An SQL error occurred");
    } else {
      larkin.sendData(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
    }
  });
}
