var api = require("../api"),
    larkin = require("../larkin"),
    topojson = require("topojson"),
    grid = require("brute-force-equal-area");

module.exports = function(req, res, next) {
  if (!req.query.latSpacing || !req.query.cellArea) {
    return larkin.info(req, res, next);
  }

  grid.longitude(parseFloat(req.query.latSpacing), parseFloat(req.query.cellArea), function(geojson) {
    if (req.query.format === "topojson" || req.query.format === "topojson_bare") {
      geojson = topojson.topology({grid: geojson});
    }

    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
    }, {
      data: geojson
    });
  });

}
