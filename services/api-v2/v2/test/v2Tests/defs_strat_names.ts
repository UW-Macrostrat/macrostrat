module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/api/v2/defs/strat_names")
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
      .get("/api/v2/defs/strat_names?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat id", function (done) {
    request(settings.host)
      .get("/api/v2/defs/strat_names?strat_name_id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept multiple strat ids", function (done) {
    request(settings.host)
      .get("/api/v2/defs/strat_names?strat_name_id=2188,7145")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res) {
        if (res.body.success.data.length != 2) {
          throw new Error(
            "defs/strat_names does not return two results as expected",
          );
        }
      })
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat name", function (done) {
    request(settings.host)
      .get("/api/v2/defs/strat_names?strat_name=Abercrombie")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat rank", function (done) {
    request(settings.host)
      .get("/api/v2/defs/strat_names?rank=Gp")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all strat names", function (done) {
    request(settings.host)
      .get("/api/v2/defs/strat_names?all")
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
      .get("/api/v2/defs/strat_names?strat_name=Abercrombie&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });
};
