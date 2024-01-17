module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/api/v2/defs/structures")
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
      .get("/api/v2/defs/structures?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept structure IDs", function (done) {
    request(settings.host)
      .get("/api/v2/defs/structures?structure_id=3,4")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res) {
        if (res.body.success.data.length !== 2) {
          throw new Error("Should have returned 2 structures but did not");
        }
      })
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a structure class", function (done) {
    request(settings.host)
      .get("/api/v2/defs/structures?structure_class=fabric")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res) {
        res.body.success.data.forEach(function (d) {
          if (d.class != "fabric") {
            throw new Error("Wrong structure class returned");
          }
        });
      })
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a structure type", function (done) {
    request(settings.host)
      .get("/api/v2/defs/structures?structure_type=fault")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res) {
        res.body.success.data.forEach(function (d) {
          if (d.structure_type != "fault") {
            throw new Error("Wrong structure type returned");
          }
        });
      })
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all definitions", function (done) {
    request(settings.host)
      .get("/api/v2/defs/structures?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return CSV", function (done) {
    request(settings.host)
      .get("/api/v2/defs/structures?structure_type=fabric&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });
};
