var api = require("../api"),
  async = require("async"),
  wellknown = require("wellknown"),
  larkin = require("../larkin");

module.exports = function (req, res, next) {
  if (req.body.layer) {
    req.body.layer = JSON.parse(req.body.layer);
    async.each(
      req.body.layer.features,
      function (feature, callback) {
        larkin.queryPg(
          "macrostrat_editing",
          "SELECT ST_isValid(ST_GeomFromText( '" +
            wellknown.stringify(feature.geometry) +
            "')) AS isvalid",
          [],
          function (error, result) {
            if (result.rows[0].isvalid) {
              callback();
            } else {
              callback("invalid");
            }
          },
        );
      },
      function (error) {
        if (error) {
          larkin.sendData([{ update: "failed" }], res, null, next);
        } else {
          async.each(
            req.body.layer.features,
            function (feature, callback) {
              larkin.queryPg(
                "macrostrat_editing",
                "UPDATE col_areas SET geom = ST_GeomFromText('" +
                  wellknown.stringify(feature.geometry) +
                  "') WHERE col_id = $1",
                [feature.properties.col_id],
                function (error, result) {
                  callback();
                },
              );
            },
            function (error) {
              larkin.sendData([{ update: "success" }], res, null, next);
            },
          );
        }
      },
    );
  } else {
    larkin.error(req, res, next, "A layer is required");
  }
};
