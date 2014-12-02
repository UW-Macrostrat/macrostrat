var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  var where = "",
      params = [];

  if (req.query.hasOwnProperty("all")) {
    // do nothing
  } else if (req.query.col_id) {
    where = "WHERE s.col_id = ?"
    params.push(req.query.col_id);
  } else {
    return larkin.error(req, res, next, "An invalid parameter was passed");
  }
  larkin.query("SELECT s.id, s.col_id, ints.interval_name AS bottom, ints2.interval_name AS top, count(u.id) AS units, COALESCE(r.fossils,0) AS fossils \
   FROM sections s \
    JOIN intervals ints on FO = ints.id \
    JOIN intervals ints2 on LO = ints2.id \
    JOIN units u ON u.section_id = s.id \
    LEFT JOIN ( \
        SELECT u.section_id, count(pbdb.id) as fossils FROM units u \
        JOIN pbdb_matches pbdb on pbdb.unit_id = u.id \
        GROUP BY u.section_id \
    ) r ON r.section_id = s.id \
   " + where +    
  " GROUP BY s.id", params, function(error, result) {
    if (error) {
      larkin.error(req, res, next, "An SQL error occurred");
    } else {
      larkin.sendData(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
    }
  });
}
