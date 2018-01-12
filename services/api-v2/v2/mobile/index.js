var express = require("express");
var mobile = express.Router();
var larkin = require("../larkin");

mobile.route("/")
  .get(function(req, res, next) {
    larkin.defineCategory("mobile", function(error, routes) {
      res.json({
        "success": routes
      });
    });
  }
);


mobile.route("/point")
  .get(require("./point"));

mobile.route("/point_details")
  .get(require("./point_details"));

mobile.route("/fossil_collections")
  .get(require("./fossil_collections"));

mobile.route("/macro_summary")
  .get(require("./macro_summary"));

mobile.route("/map_query")
  .get(require("./map_query"));

mobile.route("/map_query_v2")
  .get(require("./map_query_v2"));

module.exports =  mobile;
