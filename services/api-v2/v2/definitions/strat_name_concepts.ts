const api = require("../api");
const larkin = require("../larkin");

module.exports = function (req, res, next, cb) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  let sql = `SELECT
      snm.concept_id as concept_id,
      snm.name,
      COALESCE(snm.geologic_age::text, '') geologic_age,
      COALESCE(snm.interval_id::text, '') int_id,
      COALESCE(snm.b_int::text, '') b_int_id,
      COALESCE(snm.t_int::text, '') t_int_id,
      COALESCE(snm.usage_notes, '') usage_notes,
      COALESCE(snm.other, '') other,
      COALESCE(snm.province, '') province,
      STRING_AGG(snm.ref_id::text, '|') AS refs,
      COALESCE(snm.url, '') url,
      refs.author
     FROM macrostrat.strat_names_meta snm
     JOIN macrostrat.refs ON snm.ref_id = refs.id`;

  let params = {};
  let where = [];

  if ("all" in req.query) {
    // do nothing
  } else if (req.query.concept_like) {
    where.push("lower(name) ILIKE lower(:name)");
    params["name"] = req.query.concept_like + "%";
  } else if ("concept_name" in req.query) {
    where.push("name = ANY(:concept_name)");
    params["concept_name"] = req.query.concept_name;
  } else if (req.query.concept_id || req.query.strat_name_concept_id) {
    where.push("concept_id = ANY(:concept_id)");
    if (req.query.concept_id) {
      params["concept_id"] = larkin.parseMultipleIds(req.query.concept_id);
    } else {
      params["concept_id"] = larkin.parseMultipleIds(
        req.query.strat_name_concept_id,
      );
    }
  } else if ("name" in req.query) {
    where.push("name = ANY(:concept_name)");
    params["concept_name"] = req.query.name;
  } else if (req.query.strat_name_id) {
    where.push(
      "concept_id IN (SELECT concept_id FROM macrostrat.lookup_strat_names WHERE strat_name_id IN (:strat_name_ids))",
    );
    params["strat_name_ids"] = larkin.parseMultipleIds(req.query.strat_name_id);
  }

  // pagination
  const lastId = req.query.last_id ? parseInt(req.query.last_id, 10) : null;
  const pageSize = req.query.page_size ? parseInt(req.query.page_size, 10) : 5; // defaults to 5

  if (req.query.last_id) {
    where.push("concept_id > :last_id");
    params["last_id"] = lastId;
  }

  if (where.length > 0) {
    sql += " WHERE " + where.join(" AND ");
  }

  sql += " GROUP BY concept_id, author ORDER BY concept_id";

  if ("sample" in req.query || req.query.last_id) {
    sql += " LIMIT :page_size";
    params["page_size"] = pageSize;
  }

  larkin.queryPg("burwell", sql, params, function (error, result) {
    if (error) {
      if (cb) {
        return cb(error);
      } else {
        return larkin.error(req, res, next, error);
      }
    } else {
      /*TODO: update data types and foreach function.
      result.forEach(function (d) {
        d.int_id = parseInt(d.int_id);
        d.refs = larkin.jsonifyPipes(d.refs, "integers");
      });*/

      if (cb) {
        cb(null, result.rows);
      } else {
        larkin.sendData(
          req,
          res,
          next,
          {
            format: api.acceptedFormats.standard[req.query.format]
              ? req.query.format
              : "json",
            bare: !!api.acceptedFormats.bare[req.query.format],
            refs: "refs",
          },
          {
            data: result.rows,
          },
        );
      }
    }
  });
};
