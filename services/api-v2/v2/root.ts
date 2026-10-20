var api = require("./api");

import defs from "./defs";

module.exports = function (req, res, next) {
  var routes = {};
  api.stack.filter(function (d) {
    if (
      d.route &&
      d.route.path !== "*" &&
      d.route.path !== null &&
      d.route.path.length
    ) {
      if (defs[d.route.path] && defs[d.route.path].visible) {
        routes[d.route.path] =
          defs[d.route.path] && defs[d.route.path].description
            ? defs[d.route.path].description
            : "";
      }
    }
  });

  Object.keys(defs).filter(function (d) {
    if (defs[d].isParent) {
      routes[d] = defs[d].description;
    }
  });

  res.json({
    success: {
      v: api.version,
      description: "This is the root of the Macrostrat API",
      changelog: "/changes",
      license: api.license + ". More info at /meta",
      routes: routes,
    },
  });
};
