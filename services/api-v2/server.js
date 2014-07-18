var express = require('express'),
    routes = require('./routes/api'),
    app = express(),
    larkin = require("./larkin");

// Connect to the database
larkin.connectMySQL();

// Load and prefix all routes with /api
app.use('/api', routes);

if (process.env.NODE_ENV !== "production") {
  app.set('json spaces', 2);
}

var port = 5000;
app.listen(port, function() {
  larkin.log("info", "Listening on port " + port);
});