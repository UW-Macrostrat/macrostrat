module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/api/v2/defs/projects")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a sample", function (done) {
    request(settings.host)
      .get("/api/v2/defs/projects?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all projects", function (done) {
    request(settings.host)
      .get("/api/v2/defs/projects?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output CSV", function (done) {
    request(settings.host)
      .get("/api/v2/defs/projects?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });
};
