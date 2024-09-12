module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/defs/minerals")
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
      .get("/defs/minerals?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a mineral_id", function (done) {
    request(settings.host)
      .get("/defs/minerals?mineral_id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a mineral name", function (done) {
    request(settings.host)
      .get("/defs/minerals?mineral=abhurite")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a mineral type", function (done) {
    request(settings.host)
      .get("/defs/minerals?minerals?mineral_type=clinopyroxene")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all definitions", function (done) {
    request(settings.host)
      .get("/defs/minerals?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return CSV", function (done) {
    request(settings.host)
      .get("/defs/minerals?mineral=abhurite&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
};
