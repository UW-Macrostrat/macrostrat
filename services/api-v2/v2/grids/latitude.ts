var api = require("../api"),
    larkin = require("../larkin"),
    topojson = require("topojson"),
    grid = require("brute-force-equal-area");

module.exports = function(req, res, next) {
  if (!req.query || !req.query.lngSpacing || !req.query.latSpacing) {
    return larkin.info(req, res, next);
  }

  grid.latitude(parseFloat(req.query.lngSpacing), parseFloat(req.query.latSpacing), function(geojson) {
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
