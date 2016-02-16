var api = require("./api"),
    larkin = require("./larkin");

module.exports = function(req, res, next) {
  larkin.sendData(req, res, next, {
    format: "json",
    bare: (api.acceptedFormats.bare[req.query.format]) ? true : false
  }, {
    data: {
      "license": "All data are licensed under Creative Commons BY 4.0 International",
      "citation": "Peters, S.E. et al. Macrostrat: a platform for geological data integration and deep-time research. https://macrostrat.org, accessed on (date)",
      "api": [
        "John J Czaplewski",
        "Puneet Kishor",
        "Shanan E Peters"
      ]
    },
    support: {
      "current_funding": "U.S. National Science Foundation Grant EAR-1150082 and ICER-1440312. Additional support from the University of Wisconsin-Madison Dept. of Geoscience.",
      "previous_funding": "Initial database development supported by the United States Geological Survey and the American Chemical Society."
    }
    acknowledgements: {
      "data_entry": "University of Michigan Undergraduate Research Opportunity program, Noel Heim, Deb Rook, Neal Auchter, Annaka Clement, Clay Kelly.",
      "contributors": ["Jon Husson"],
      "data_providers": "The data synthesized in Macrostrat reflect the combined work of hundreds of field-based geoscientists. These contributors are too many to cite individually, but see /defs/refs?all and /defs/sources?all for a list of primary sources supplying data and the references therein."
    }
  });

}
