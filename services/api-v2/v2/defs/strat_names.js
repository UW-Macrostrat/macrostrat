var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var where = [],
      params = {};

  if (req.query.strat_name_id) {
    where.push("(bed_id IN (:strat_name_id) or mbr_id IN (:strat_name_id) or fm_id IN (:strat_name_id) or gp_id IN (:strat_name_id) or sgp_id IN (:strat_name_id))");
    params["strat_name_id"] = larkin.parseMultipleIds(req.query.strat_name_id);

  } else if (req.query.strat_name_like) {
    where.push("strat_name LIKE :strat_name");
    params["strat_name"] = req.query.strat_name_like + "%";

  } else if (req.query.strat_name) {
    where.push("strat_name LIKE :strat_name");
    params["strat_name"] = req.query.strat_name;
  } 

  if (req.query.rank) {
    where.push("rank = :rank");
    params["rank"] = req.query.rank;
  }

  var sql = "SELECT strat_name, rank, strat_name_id, bed_name bed,bed_id, mbr_name mbr, mbr_id, fm_name fm, fm_id, gp_name gp, gp_id, sgp_name sgp, sgp_id, early_age AS b_age, late_age AS t_age, gsc_lexicon FROM lookup_strat_names";

  if (where.length > 0) {
    sql += " WHERE " + where.join(" AND ")
  }

  larkin.query(sql, params, null, true, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
}
