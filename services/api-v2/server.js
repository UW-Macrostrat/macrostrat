var express = require("express"),
    bodyParser = require("body-parser"),
    v1 = require("./v1"),
    v2 = require("./v2"),
    app = express();

/*
var keenio = require("express-keenio");

keenio.configure({
  client: {
    projectId: "56e6fb7690e4bd5b3b1acba4",
    writeKey: "ee3b2b574b8e54e9d92748cffad9c0354e973739fd928c3f5091039bae0f17ec7ba6d6b61c15754e8b5656837f65b3d0f9f36f45a7d8543df9210f1e60468ae3f07c70dc9ae81d691b3f04c09f319c2541518813ee33d50f8fa5d938b56c529f"
  },
  excludeRoutes: [
    { method: 'GET', route: 'maps'}
  ]
});

app.use(keenio.handleAll());
*/
// parse application/x-www-form-urlencoded
app.use(bodyParser.urlencoded({ extended: false }))

// parse application/json
app.use(bodyParser.json())

// parse application/vnd.api+json as json
app.use(bodyParser.json({ type: "application/vnd.api+json" }))

// Load and prefix all routes with /api and appropriate version
app.use("/api/v1", v1);
app.use("/api/v2", v2);

// If no version specified, fall back to more current
app.use("/api", v2);

app.set("json spaces", 2);

app.port = process.argv[2] || 5000;

app.start = function() {
  app.listen(app.port, function() {
    console.log("Listening on port " + app.port);
  });
}

if (!module.parent) {
  app.start();
}


module.exports = app;
