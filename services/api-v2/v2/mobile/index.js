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

module.exports =  mobile;
