var api = require("../api"),
    larkin = require("../larkin"),
    multiline = require("multiline");

module.exports = function(req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = multiline(function() {/*
    SELECT
      snm.concept_id as concept_id,
      snm.name,
      COALESCE(snm.geologic_age, '') geologic_age,
      COALESCE(snm.interval_id, '') int_id,
      COALESCE(snm.b_int, '') b_int_id,
      COALESCE(snm.t_int, '') t_int_id,
      COALESCE(snm.usage_notes, '') usage_notes,
      COALESCE(snm.other, '') other,
      COALESCE(snm.province, '') province,
      GROUP_CONCAT(snm.ref_id SEPARATOR '|') AS refs,
      COALESCE(snm.url, '') url,
      refs.author
     FROM strat_names_meta snm
     JOIN refs ON snm.ref_id = refs.id
  */}),
      params = {};

  if ("all" in req.query) {
    // do nothing
  } else if ("concept_name" in req.query) {
    sql += " WHERE name IN (:concept_name)";
    params["concept_name"] = req.query.concept_name;
  } else if (req.query.concept_id || req.query.strat_name_concept_id) {
    sql += " WHERE concept_id IN (:concept_id)";
    if (req.query.concept_id) {
      params["concept_id"] = larkin.parseMultipleIds(req.query.concept_id);
    } else {
      params["concept_id"] = larkin.parseMultipleIds(req.query.strat_name_concept_id);
    }

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
      if (cb) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }

    } else {
      result.forEach(function(d) {
        d.int_id = parseInt(d.int_id);
        d.refs = larkin.jsonifyPipes(d.refs, "integers");
      });

      if (cb) {
        cb(null, result);
      } else {
        larkin.sendData(req, res, next, {
          format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
          bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
          refs: "refs"
        }, {
          data: result
        });
      }

    }
  });
}
