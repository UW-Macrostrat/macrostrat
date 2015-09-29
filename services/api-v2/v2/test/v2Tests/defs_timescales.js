module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");
  
  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v2/defs/timescales")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a sample", function(done) {
    request(settings.host)
      .get("/api/v2/defs/timescales?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all timescales", function(done) {
    request(settings.host)
      .get("/api/v2/defs/timescales?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output CSV", function(done) {
    request(settings.host)
      .get("/api/v2/defs/timescales?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

}
