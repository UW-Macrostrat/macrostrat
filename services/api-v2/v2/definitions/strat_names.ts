var api = require("../api"),
  larkin = require("../larkin"),
  multiline = require("multiline");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var where = [],
    params = {};

  if (req.query.rule) {
    if (req.query.rule === "down") {
      if (req.query.strat_name) {
        where.push(
          "parent IN (SELECT strat_name_id FROM macrostrat.lookup_strat_names WHERE strat_name = :strat_name) OR strat_name_id = ANY(SELECT strat_name_id FROM macrostrat.lookup_strat_names WHERE strat_name = :strat_name)",
        );
        params["strat_name"] = req.query.strat_name;
      } else if (req.query.strat_name_id) {
        where.push(
          "parent IN (:strat_name_id) OR l.strat_name_id = ANY(:strat_name_id)",
        );
        params["strat_name_id"] = larkin.parseMultipleIds(
          req.query.strat_name_id,
        );
      } else if (req.query.concept_id) {
        where.push(
          "parent IN (( SELECT DISTINCT strat_name_id FROM macrostrat.lookup_strat_names WHERE concept_id = ANY(:concept_id) )) OR l.strat_name_id = ANY(( SELECT DISTINCT strat_name_id FROM macrostrat.lookup_strat_names WHERE concept_id IN (:concept_id) ))",
        );
        params["concept_id"] = larkin.parseMultipleIds(req.query.concept_id);
      }
    } else if (req.query.rule === "all") {
      if (req.query.strat_name) {
        where.push(
          "tree = (SELECT tree FROM macrostrat.lookup_strat_names WHERE strat_name = :strat_name)",
        );
        params["strat_name"] = req.query.strat_name;
      } else if (req.query.strat_name_id) {
        where.push(
          "tree = (SELECT tree FROM macrostrat.lookup_strat_names WHERE strat_name_id IN (:strat_name_id))",
        );
        params["strat_name_id"] = larkin.parseMultipleIds(
          req.query.strat_name_id,
        );
      }
    }
  } else {
    if (req.query.strat_name_id) {
      where.push("strat_name_id = ANY(:strat_name_id)");
      params["strat_name_id"] = larkin.parseMultipleIds(
        req.query.strat_name_id,
      );
    } else if (req.query.strat_name_like) {
      where.push("lower(strat_name) ILIKE lower(:strat_name)");
      params["strat_name"] = req.query.strat_name_like + "%";
    } else if (req.query.strat_name) {
      where.push("lower(strat_name) ILIKE lower(:strat_name)");
      params["strat_name"] = req.query.strat_name;
    } else if (req.query.concept_id) {
      where.push("concept_id = ANY(:concept_id)");
      params["concept_id"] = larkin.parseMultipleIds(req.query.concept_id);
    } else if (req.query.strat_name_concept_id) {
      where.push("concept_id = ANY(:concept_id)");
      params["concept_id"] = larkin.parseMultipleIds(
        req.query.strat_name_concept_id,
      );
    }

    if (req.query.interval_name) {
      where.push(
        "early_age > (SELECT age_top from macrostrat.intervals where interval_name like :interval_name) and late_age < (SELECT age_bottom from macrostrat.intervals where interval_name like :interval_name2)",
      );
      params["interval_name"] = larkin.parseMultipleStrings(
        req.query.interval_name,
      );
      params["interval_name2"] = larkin.parseMultipleStrings(
        req.query.interval_name,
      );
    }

    if (req.query.ref_id) {
      where.push("ref_id = ANY(:ref_id)");
      params["ref_id"] = larkin.parseMultipleIds(req.query.ref_id);
    }

    if (req.query.rank) {
      where.push("rank = :rank");
      params["rank"] = req.query.rank;
    }

    if (req.query.ref_id) {
      where.push("ref_id = ANY(:ref_ids)");
      params["ref_ids"] = larkin.parseMultipleIds(req.query.ref_id);
    }
  }

  var sql = `
    SELECT
      strat_name,
      rank_name AS strat_name_long,
      rank,
      strat_name_id,
      concept_id AS concept_id,
      COALESCE(bed_name, '') AS bed,
      bed_id,
      COALESCE(mbr_name, '') AS mbr,
      mbr_id,
      COALESCE(fm_name, '') AS fm,
      fm_id,
      COALESCE(subgp_name, '') AS subgp,
      subgp_id,
      COALESCE(gp_name, '') AS gp,
      gp_id,
      COALESCE(sgp_name, '') AS sgp,
      sgp_id,
      early_age AS b_age,
      late_age AS t_age,
      COALESCE(b_period, '') AS b_period,
      COALESCE(t_period, '') AS t_period,
      COALESCE(c_interval, '') AS c_interval,
      t_units,
      ref_id
    FROM macrostrat.lookup_strat_names l
  `;

  if (where.length > 0) {
    sql += " WHERE " + where.join(" AND ");
  }

  if ("sample" in req.query) {
    sql += " LIMIT 5";
  }

  larkin.queryPg("burwell", sql, params, function (error, response) {
    if (error) {
      console.log(error);
      if (cb) {
        cb(error);
      } else {
        larkin.error(req, res, next, "Something went wrong");
      }
    } else {
      if (cb) {
        cb(null, response.rows);
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
            refs: "ref_id",
          },
          {
            data: response.rows,
          },
        );
      }
    }
  });
};
