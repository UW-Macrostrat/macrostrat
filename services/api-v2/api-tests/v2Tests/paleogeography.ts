module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/paleogeography")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a sample", function (done) {
    request(settings.host)
      .get("/paleogeography?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an age parameter", function (done) {
    request(settings.host)
      .get("/paleogeography?age=271")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an interval name", function (done) {
    request(settings.host)
      .get("/paleogeography?interval_name=Permian")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return topojson", function (done) {
    request(settings.host)
      .get("/paleogeography?interval_name=Permian&format=topojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.topoJSON)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
};
