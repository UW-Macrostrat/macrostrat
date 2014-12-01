var express = require("express"),
    v1 = require("./v1/index"),
    larkinV1 = require("./v1/larkin"),
    bodyParser = require("body-parser"),
    app = express();

// Connect to the database
larkinV1.connectMySQL();

// parse application/x-www-form-urlencoded
app.use(bodyParser.urlencoded({ extended: false }))

// parse application/json
app.use(bodyParser.json())

// parse application/vnd.api+json as json
app.use(bodyParser.json({ type: "application/vnd.api+json" }))

// Load and prefix all routes with /api and appropriate version
app.use("/api/v1", v1);

// If no version specified, fall back to more current
app.use("/api", v1);

if (process.env.NODE_ENV !== "production") {
  app.set("json spaces", 2);
}

var port = 5000;
app.listen(port, function() {
  larkinV1.log("info", "Listening on port " + port);
});
