module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v2/defs/lithology_attributes")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an att_type", function(done) {
    request(settings.host)
      .get("/api/v2/defs/lithology_attributes?att_type=bedform")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith_att", function(done) {
    request(settings.host)
      .get("/api/v2/defs/lithology_attributes?lith_att=mounds")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith att id", function(done) {
    request(settings.host)
      .get("/api/v2/defs/lithology_attributes?id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all records", function(done) {
    request(settings.host)
      .get("/api/v2/defs/lithology_attributes?all")
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
      .get("/api/v2/defs/lithology_attributes?lith_att=mounds&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
