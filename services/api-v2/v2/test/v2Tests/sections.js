module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return metadata", function(done) {
    request(settings.host)
      .get("/api/v2/sections")
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
      .get("/api/v2/sections?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a column id", function(done) {
    request(settings.host)
      .get("/api/v2/sections?col_id=49")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return csv", function(done) {
    request(settings.host)
      .get("/api/v2/sections?col_id=17&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
