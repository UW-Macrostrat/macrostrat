var api = require("../api"),
    larkin = require("../larkin"),
    multiline = require("multiline");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = multiline(function() {/*
    SELECT
      concept_id,
      name,
      COALESCE(geologic_age, '') geologic_age,
      COALESCE(interval_id, '') int_id,
      COALESCE(usage_notes, '') usage_notes,
      COALESCE(other, '') other,
      COALESCE(province, '') province,
      GROUP_CONCAT(ref_id SEPARATOR '|') AS refs
     FROM strat_names_meta
  */}),
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.strat_name_concept_id) {
    sql += " WHERE concept_id IN (:concept_id)";
    params["concept_id"] = larkin.parseMultipleIds(req.query.strat_name_concept_id);
  } else if (req.query.strat_name_id) {
    sql += " WHERE concept_id IN (SELECT concept_id FROM lookup_strat_names WHERE strat_name_id IN (:strat_name_ids))";
    params["strat_name_ids"] = larkin.parseMultipleIds(req.query.strat_name_id);
  }

  sql += " GROUP BY concept_id ORDER BY concept_id";

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.query(sql, params, function(error, result) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      result.forEach(function(d) {
        d.int_id = parseInt(d.int_id);
        d.refs = larkin.jsonifyPipes(d.refs, "integers");
      });
      larkin.sendData(result, res, ((api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"), next);
    }
  });
}
