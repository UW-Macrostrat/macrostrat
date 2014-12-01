var express = require("express"),
    routes = require("./routes/api"),
    app = express(),
    larkin = require("./larkin"),
    bodyParser = require("body-parser");

// Connect to the database
larkin.connectMySQL();

// parse application/x-www-form-urlencoded
app.use(bodyParser.urlencoded({ extended: false }))

// parse application/json
app.use(bodyParser.json())

// parse application/vnd.api+json as json
app.use(bodyParser.json({ type: "application/vnd.api+json" }))

// Load and prefix all routes with /api
app.use("/api", routes);

if (process.env.NODE_ENV !== "production") {
  app.set("json spaces", 2);
}

var port = 5000;
app.listen(port, function() {
  larkin.log("info", "Listening on port " + port);
});
