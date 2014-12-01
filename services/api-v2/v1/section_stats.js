var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  if ("all" in req.query) {
    var sql = "\
    SELECT project, units_sections.col_id col_id, units_sections.section_id section_id, count(distinct units.id) units, sum(max_thick) max_thick, sum(min_thick) min_thick, max(FO_age) FO_age, min(LO_age) LO_age, max(ub2.t1_age) b_age, min(ub1.t1_age) t_age \
    FROM units \
    JOIN units_sections ON units.id=unit_id \
    JOIN cols ON units_sections.col_id=cols.id \
    JOIN projects on project_id=projects.id \
    JOIN lookup_unit_intervals ON units_sections.unit_id=lookup_unit_intervals.unit_id \
    JOIN unit_boundaries ub1 ON units_sections.unit_id=ub1.unit_id \
    JOIN unit_boundaries ub2 ON units_sections.unit_id=ub2.unit_id_2 \
    WHERE status_code='active' and units.id IN (SELECT distinct unit_id from unit_liths,liths where lith_id=liths.id and lith_class='sedimentary') and FO_age<=541 GROUP BY units_sections.section_id;";
  } else {
    return larkin.error(req, res, next, "Invalid parameters");
  }

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";

  larkin.query(sql, [], null, true, res, format, next);
}