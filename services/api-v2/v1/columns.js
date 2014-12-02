var api = require("./api"),
    async = require("async"),
    dbgeo = require("dbgeo"),
    gp = require("geojson-precision"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  async.waterfall([
    function(callback) {
      if (req.query.interval_name) {
        larkin.query("SELECT age_bottom,age_top,interval_name from intervals where interval_name = ? LIMIT 1", [req.query.interval_name], function(error, result) {
          if (error) {
            callback(error);
          } else {
            if (result.length === 0) {
              callback("No results found");
            } else {
              callback(null, {"interval_name": result[0].interval_name, "age_bottom": result[0].age_bottom, "age_top": result[0].age_top});
              }
            }
          }
        );
      } else if (req.query.age) {
        callback(null, {"interval_name": "Unknown", "age_bottom": req.query.age, "age_top": req.query.age});
      } else if (req.query.age_top && req.query.age_bottom) {
        callback(null, {"interval_name": "Unknown", "age_bottom": req.query.age_bottom, "age_top": req.query.age_top});
      } else if (req.query.hasOwnProperty("all")) {
        callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0});
      } else if (req.query.lith_type || req.query.lith_class || req.query.lith){
        callback(null, {"interval_name": "Unknown", "age_bottom": 9999, "age_top": 0});
      }
        else {
        larkin.error(req, res, next, "An invalid parameter was given");
      }
    },
    function(data, callback) {
      var lith = '%',
          lith_field = 'lith';
      if (req.query.lith){
        lith = req.query.lith;
      } else if (req.query.lith_class){
        lith = req.query.lith_class;
        lith_field = 'lith_class';
      } else if (req.query.lith_type){
        lith = req.query.lith_type;
        lith_field = 'lith_type';
      }
      larkin.query("SELECT " + ((req.query.format && api.acceptedFormats.geo[req.query.format]) ? "AsWKT(col_areas.col_area) AS wkt," : "") + " col_areas.col_id, round(cols.col_area, 1) AS area, GROUP_CONCAT(units.id SEPARATOR '|') AS units, sum(max_thick) max_thick, sum(min_thick) min_thick, sum(LT.cpm) lith_max_thick, sum(LT.cpl) lith_min_thick,  LT2.lts lith_types \
        FROM col_areas \
        JOIN cols ON cols.id = col_areas.col_id \
        JOIN units_sections ON units_sections.col_id = cols.id \
        JOIN units ON unit_id = units.id \
        JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id = units_sections.unit_id \
        JOIN (SELECT unit_id, round(sum(comp_prop*max_thick), 1) cpm, round(sum(comp_prop*min_thick), 1) cpl FROM unit_liths JOIN liths on lith_id=liths.id JOIN units on unit_id=units.id WHERE ?? like ? GROUP BY unit_id) LT ON LT.unit_id=units.id \
        JOIN (SELECT col_id, GROUP_CONCAT(distinct lith_type SEPARATOR '|') lts from liths JOIN unit_liths on lith_id=liths.id JOIN units_sections ON unit_liths.unit_id=units_sections.unit_id JOIN lookup_unit_intervals ON lookup_unit_intervals.unit_id=units_sections.unit_id WHERE ?? like ? AND FO_age > ? AND LO_age < ? GROUP BY col_id) LT2 on LT2.col_id=col_areas.col_id \
        WHERE FO_age > ? AND LO_age < ? AND status_code = 'active' \
        GROUP BY col_areas.col_id", [lith_field, lith, lith_field, lith, data.age_top, data.age_bottom, data.age_top, data.age_bottom], function(error, result) {
          if (error) {
            callback(error);
          } else {
            result.forEach(function(d) {
              d.units = d.units.split("|");
              d.units = d.units.map(function(j) {
                return parseInt(j);
              });
              d.lith_types = d.lith_types.split("|");
            });
            callback(null, data, result);
          }
      });
    }
  ], function(error, data, result) {
    if (error) {
      larkin.error(req, res, next, "An error was incurred");
    } else {
      if (req.query.format && api.acceptedFormats.geo[req.query.format]) {
        dbgeo.parse({
          "data": result,
          "geometryColumn": "wkt",
          "geometryType": "wkt",
          "outputFormat": larkin.getOutputFormat(req.query.format),
          "callback": function(error, output) {
            if (error) {
              larkin.error(req, res, next, "An error was incurred during conversion");
            } else {
              output.properties = data;
              if (larkin.getOutputFormat(req.query.format) === "geojson") {
                output = gp(output, 4);
              }
              if (api.acceptedFormats.bare[req.query.format]) {
                larkin.sendBare(output, res, next);
              } else {
                larkin.sendData(output, res, null, next);
              }
            }
          }
        });
      } else {
        larkin.sendData(result, res, (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json", next);
      }  
    }
  });
}
