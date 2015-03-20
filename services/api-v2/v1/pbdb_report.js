var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var where = "";
      params = [];
  if (isFinite(req.query.project_id)) {
    where += " AND project_id = ? ";
    params.push(req.query.project_id);
  } 

  var sql = "";
  if (req.query.matched) {
    sql += "SELECT count(distinct collection_no) collections, CONCAT_WS(' ', strat_name, rank) strat_name, lookup_strat_names.strat_name_id FROM pbdb_matches JOIN unit_strat_names USING (unit_id) JOIN lookup_strat_names USING (strat_name_id) JOIN units_sections USING (unit_id) JOIN cols on col_id=cols.id WHERE status_code='active' " + where + " GROUP BY pbdb_matches.unit_id";
  } else if (req.query.showpairs){
    sql += "SELECT pbdb_matches.collection_no,pbdb_matches.unit_id FROM pbdb_matches WHERE release_date < NOW() " + where + "";
  } else {
    sql += "SELECT count(distinct collection_no) AS collections, CONCAT_WS(' ', strat_name, rank) strat_name, lookup_strat_names.strat_name_id FROM lookup_strat_names JOIN unit_strat_names USING (strat_name_id) JOIN units_sections USING (unit_id) JOIN cols ON col_id=cols.id LEFT JOIN pbdb_matches USING (unit_id) WHERE status_code='active' " + where + " AND pbdb_matches.unit_id IS NULL AND lookup_strat_names.late_age < 541 GROUP BY lookup_strat_names.strat_name_id";
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, params, null, true, res, format, next);
}
