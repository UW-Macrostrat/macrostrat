var pg = require("pg"),
    async = require("async"),
    larkin = require("../larkin");

larkin.connectMySQL();

function getTopOfTree(name) {
  if (name.sgp_id > 0) {
    return name.sgp_id;
  } else if (name.gp_id > 0) {
    return name.gp_id;
  } else if (name.fm_id > 0) {
    return name.fm_id;
  } else if (name.mbr_id > 0) {
    return name.mbr_id;
  } else if (name.bed_id > 0) {
    return name.bed_id;
  }
}

async.waterfall([
  // -1: Clean up
  function(callback) {
    larkin.query("ALTER TABLE lookup_strat_names ADD COLUMN", [], function(error, response) {
      if (error) {
        callback(error);
      } else {
        callback(null);
      }
    });
  },

  // 0: Create output table
  function(callback) {
    larkin.query("CREATE TABLE lookup_strat_name_hierarchy (id serial, strat_name_id integer, parent integer, topOfTree integer)", [], function(error, response) {
      if (error) {
        callback(error);
      } else {
        callback(null);
      }
    });
  },

  // 1: Get all of our strat_names
  function(callback) {
    larkin.query("SELECT * FROM lookup_strat_names", [], function(error, data) {
      callback(null, data);
    });
  },

  // 2: Process strat_names
  function(strat_names, callback) {
    // This keeps track of pairs we have already accounted for
    var alreadyHandled = []

    // For each strat_name...
    async.each(strat_names, function(name, callbackA) {
      var topOfTree = getTopOfTree(name);
      // Create key pairs
      var pairs = [
        [name.strat_name_id, name.strat_name_id, topOfTree],
        [name.bed_id, name.mbr_id, topOfTree],
        [name.mbr_id, name.fm_id, topOfTree],
        [name.fm_id, name.gp_id, topOfTree],
        [name.gp_id, name.sgp_id, topOfTree]
      ];

      // For each pair..
      async.each(pairs, function(d, callbackB) {
        var pairString = d.join("-");
        // Make sure neither is zero...those don't mean anything...and that we haven't already inserted this one
        if (d[0] != 0 && d[1] != 0 && alreadyHandled.indexOf(pairString) < 0) {
          // Account for this unique pair
          alreadyHandled.push(pairString);

          // And insert it
          larkin.query("INSERT INTO lookup_strat_name_hierarchy (strat_name_id, parent, topOfTree) VALUES (?, ?, ?)", d, function(error, response) {
            if (error) {
              callbackB(error);
            } else {
              callbackB(null);
            }
          });
        } else {
          callbackB(null);
        }
      }, function(error) {
        if (error) {
          callbackA(error);
        } else {
          callbackA(null);
        }
      });

    }, function(error) {
      if (error) {
        callback(error);
      } else {
        callback(null);
      }
    });

  },

  // Create indices
  function(callback) {
    larkin.query("CREATE INDEX lsnh_strat_name_id ON lookup_strat_name_hierarchy (strat_name_id);", [], function(error, response) {
      if (error) {
        callback(error);
      } else {
        larkin.query("CREATE INDEX lsnh_parent ON lookup_strat_name_hierarchy (parent);", [], function(error, response) {
          if (error) {
            callback(error);
          } else {
            callback(null);
          }
        });
      }
    });
  }
], function(error, result) {
  if (error) {
    console.log(error);
  } else {
    console.log("Done building macrostrat.lookup_strat_name_hierarchy");
  }
  process.exit(0);
});

    