var api = require("../api"),
    larkin = require("../larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var filterString = "",
      params = [];

  if (req.query.all) {
    // do nothing
  } else if (req.query.id) {
    filterString += "bed_id = ? or mbr_id = ? or fm_id = ? or gp_id = ? or sgp_id = ?";
    params.push(req.query.id,req.query.id,req.query.id,req.query.id,req.query.id);
  } else if (req.query.name_like) {
    if (req.query.rank && req.query.rank.length <= 3 && req.query.rank.length >= 2 && /^[a-zA-Z]+$/.test(req.query.rank)){
      filterString += req.query.rank+"_name LIKE ?";
      params.push(req.query.name_like + "%");
    } else {
      filterString += "strat_name LIKE ?";
      params.push(req.query.name_like + "%");}
  } else if (req.query.name) {
    if (req.query.rank && req.query.rank.length <= 3 && req.query.rank.length >= 2 && /^[a-zA-Z]+$/.test(req.query.rank)){
      filterString += req.query.rank+"_name LIKE ?";
      params.push(req.query.name);
    } else {
      filterString += "strat_name LIKE ?";
      params.push(req.query.name);}
  } else if (req.query.rank) {
    filterString += "rank = ?";
    params.push(req.query.rank);
  }

  if (filterString.length > 1) {
    filterString = " WHERE " + filterString;
  }

  var sql = "SELECT strat_name name, rank, strat_name_id id, bed_name bed,bed_id,mbr_name mbr,mbr_id,fm_name fm,fm_id,gp_name gp,gp_id,sgp_name sgp,sgp_id,early_age,late_age,gsc_lexicon FROM lookup_strat_names" + filterString;

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, params, null, true, res, format, next);
}
