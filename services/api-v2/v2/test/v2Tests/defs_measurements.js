module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v2/defs/measurements")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept measurement IDs", function(done) {
    request(settings.host)
      .get("/api/v2/defs/measurements?measure_id=3,4")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length !== 2) {
          throw new Error("Should have returned 2 measurements but did not");
        } 
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a measurement class", function(done) {
    request(settings.host)
      .get("/api/v2/defs/measurements?measurement_class=geochemical")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        res.body.success.data.forEach(function(d) {
          if (d.measurement_class != "geochemical") {
            throw new Error("Wrong measurement class returned");
          }
        })
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a measurement type", function(done) {
    request(settings.host)
      .get("/api/v2/defs/measurements?measurement_type=geochronological")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        res.body.success.data.forEach(function(d) {
          if (d.measurement_type != "geochronological") {
            throw new Error("Wrong measurement type returned");
          }
        })
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all definitions", function(done) {
    request(settings.host)
      .get("/api/v2/defs/measurements?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return CSV", function(done) {
    request(settings.host)
      .get("/api/v2/defs/measurements?measurement_type=geochronological&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
