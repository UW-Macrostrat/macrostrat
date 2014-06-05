var express = require('express'),
  router = require('./routes/router'),
  app = express(),
  api = require("./api");

app.use(express.logger());

// set .html as the default extension for views
app.set('view engine', 'html');
 
app.use(app.router);

// GZIP responses
app.use(express.compress());

app.enable('trust proxy');

api.connectMySQL();

app.all('/api/*', function(req, res, next) {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "X-Requested-With");
  next();
});

// Page routes
app.get('/api', router.root);
app.get('/api/columns', router.columns);
app.get('/api/fossils', router.fossils);
app.get('/api/strats', router.strats);
app.get('/api/stats', router.stats);
app.get('/api/units', router.units);

// Handle 404
app.use(function(req, res) {
   res.send('404: Page not Found', 404);
});

// Handle 500
app.use(function(error, req, res, next) {
   res.send('500: Internal Server Error', 500);
});

var port = 5000;
app.listen(port, function() {
  console.log("Listening on port " + port);
});