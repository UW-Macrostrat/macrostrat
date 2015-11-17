var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  larkin.sendData(req, res, next, {
    format: "json",
    bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
  }, {
    data: {
      "license": "All data is licensed under Creative Commons BY 4.0 International",
      "citation": "",
      "authors": [
        "John J Czaplewski",
        "Shanan E Peters",
        "Puneet Kishor"
      ]
    }
  });

}
