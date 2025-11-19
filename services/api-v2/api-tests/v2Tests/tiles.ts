var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");
//TODO need to modify these tests to work with the tileserver api

const baseURL = "https://tiles.dev.macrostrat.org";
const tilePath = "/maps/bounds/3/2/4";

describe("Tileserver API", function () {
  this.timeout(10000);
  it("should return a valid tile response", function (done) {
    request(baseURL)
      .get(tilePath)
      .expect(200)
      .expect("content-type", /application\/x-protobuf/)
      .end(function (err, res) {
        if (err) return done(err);
        if (
          !res.headers["content-length"] ||
          res.headers["content-length"] < 100
        ) {
          return done(new Error("Tile is empty or too small"));
        }
        done();
      });
  });

  it("should return gzip-compressed protobuf data", function (done) {
    request(baseURL)
      .get(tilePath)
      .expect(200)
      .end(function (err, res) {
        if (err) return done(err);
        const encoding = res.headers["content-encoding"];
        if (encoding !== "gzip") {
          return done(new Error(`Expected gzip compression, got: ${encoding}`));
        }
        if (!/application\/x-protobuf/.test(res.headers["content-type"])) {
          return done(
            new Error(
              `Unexpected content-type: ${res.headers["content-type"]}`,
            ),
          );
        }
        done();
      });
  });

  it("should include Varnish and cache headers", function (done) {
    request(baseURL)
      .get(tilePath)
      .expect(200)
      .end(function (err, res) {
        if (err) return done(err);
        if (!res.headers["server"] || !/uvicorn/i.test(res.headers["server"])) {
          return done(new Error("Missing or incorrect server header"));
        }
        if (!res.headers["x-cache"]) {
          return done(new Error("Missing x-cache header"));
        }
        if (!res.headers["x-varnish"]) {
          return done(new Error("Missing x-varnish header"));
        }
        done();
      });
  });
});
