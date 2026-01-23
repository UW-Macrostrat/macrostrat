var api = require("../api");

import defs from "../defs";

module.exports = function (req, res, next) {
  var available = {};
  for (var key in defs) {
    if (defs[key].parent && defs[key].parent === "editing") {
      available[key] = defs[key].description;
    }
  }

  res.json({
    success: {
      v: api.version,
      description: defs["/editing"].description,
      routes: available,
    },
  });
};
