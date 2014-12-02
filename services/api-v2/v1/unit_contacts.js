var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var sql = "SELECT unit_contacts.unit_id,contact,unit_contacts.with_unit FROM unit_contacts \
             LEFT JOIN units_sections us1 ON us1.unit_id=unit_contacts.unit_id \
             LEFT JOIN units_sections us2 ON us2.unit_id=unit_contacts.with_unit \
             JOIN cols c1 on us1.col_id=c1.id \
             JOIN cols c2 on us2.col_id=c2.id \
             WHERE ",
      section_id = "";

  if (req.query.all) {
    // do nothing
  } else if (req.query.section_id) {
    sql += "us1.section_id = ? and us2.section_id = ? and ";  
    section_id = req.query.section_id;
  } 

  sql += "us1.col_id=c1.id and us2.col_id=c2.id and c1.status_code='active' and c2.status_code='active'";

  var format = (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json";
  larkin.query(sql, [section_id,section_id], null, true, res, format, next);
  
}
