var express = require('express'),
  router = require('./routes/router'),
  app = express(),
  api = require("./api");

app.use(app.router);

// GZIP responses
app.use(express.compress());

app.enable('trust proxy');

// Connect to the database
api.connectMySQL();

// Make sure the world can see it
app.all('/api/*', function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "X-Requested-With");
  next();
});

// Data routes
app.get('/api', router.root);
app.get('/api/columns', router.columns);
app.get('/api/fossils', router.fossils);
app.get('/api/strats', router.strats);
app.get('/api/stats', router.stats);
app.get('/api/units', router.units);

// Handle 404
app.use(function(req, res) {
  api.error(res, next, "404: Page not found", null, 404);
});

// Handle 500
app.use(function(error, req, res, next) {
  api.error(res, next, "500: Internal Server Error", null, 500);
});

var port = 5000;
app.listen(port, function() {
  api.log("info", "Listening on port " + port);
});