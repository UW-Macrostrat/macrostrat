var async = require("async"),
  larkin = require("../larkin");

module.exports = function (req, res, next) {
    //TODO need to rewrite passcode into an ENV file.
  if (req.body.passcode && req.body.passcode === "phylum" && req.body.units) {
    async.each(
      req.body.units,
      function (each, callback) {
        larkin.queryPg("burwell",
          "UPDATE macrostrat_temp.units SET position_bottom = :position_bottom WHERE id = :units",
          [each.position_bottom, each.unit],
          function (error, result) {
            if (error) {
              callback(error);
            } else {
              callback(null);
            }
          },
        );
      },
      function (error) {
        if (error) {
          larkin.error(req, res, next, "Something went wrong");
        } else {
          res.json("worked!");
        }
      },
    );
  } else {
    if (Object.keys(req.query).length < 1) {
      return larkin.info(req, res, next);
    }
  }
};
