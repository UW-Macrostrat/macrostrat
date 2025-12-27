const dotenv = require("dotenv");
// Load environment variables from .env file
dotenv.config();

import { buildAPI } from "./v2";

var express = require("express"),
  bodyParser = require("body-parser");
//defs = require("./v2/defs"),

//TODO: update port to designated env.
const listenPort = process.argv[2] ?? process.env.PORT ?? 5000;

async function runServer() {
  const app = express();
  // parse application/x-www-form-urlencoded
  app.use(bodyParser.urlencoded({ extended: false }));

  // parse application/json
  app.use(bodyParser.json());

  // parse application/vnd.api+json as json
  app.use(bodyParser.json({ type: "application/vnd.api+json" }));

  const v2 = await buildAPI();

  // Load and prefix all routes with /api and appropriate version
  app.use("/v2", v2);

  app.route("/v1*").get(function (req, res, next) {
    res.status(410).send({
      error:
        "Macrostrat's v1 API has been retired. Please update your usage to newer endpoints.",
    });
  });

  // If no version specified, fall back to more current
  app.use("/", v2);

  app.set("json spaces", 2);

  app.listen(listenPort, function () {
    console.log("Listening on port " + listenPort);
  });
}

runServer().catch((error) => {
  console.error("Failed to start server:", error);
});
