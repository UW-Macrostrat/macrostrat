var api = require("../api"),
    larkin = require("../larkin"),
    async = require("async");

var validTypes = ["col_id", "econ_id", "econ_type", "econ_class", "environ_id", "envion_type", "environ_class", "col_group_id", "int_id", "lith_id", "lith_type", "lith_class", "lith_att_id", "strat_name_id", "strat_name_concept_id", "timescale_id"];

var routeLookup = {
  "col_id": "columns",
  "econ_id": "econs",
  "econ_type": "econs",
  "econ_class": "econs",
  "environ_id": "environments",
  "environ_type": "environments",
  "environ_class": "environments",
  "col_group_id": "groups",
  "int_id": "intervals",
  "lith_id": "lithologies",
  "lith_type": "lithologies",
  "lith_class": "lithologies",
  "lith_att_id": "lithology_attributes",
  "strat_name_id": "strat_names",
  "strat_name_concept_id": "strat_name_concepts",
  "timescale_id": "timescales"
}

module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  var toQuery = {};
  var results = {};

  Object.keys(req.query).forEach(function(d) {
    if (validTypes.indexOf(d) > -1) {
      toQuery[d] = req.query[d];
    }
  });


  async.each(Object.keys(toQuery), function(key, callback) {
    var request = {query: {}}
    request.query[key] = toQuery[key];

    require("./" + routeLookup[key])(request, null, null, function(error, data) {
      if (error) {
        return callback(error);
      }
      results[routeLookup[key]] = data;
      callback(null);
    });

  }, function(error) {
    if (error) {
      return larkin.error(req, res, next, "Error getting defitions");
    }

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json"
    }, {
      data: results
    });
  });
}
