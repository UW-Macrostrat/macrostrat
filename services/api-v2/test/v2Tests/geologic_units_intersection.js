module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return metadata", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units/intersection")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a WKT LineString", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units/intersection?LINESTRING(-91.8896484375 43.26120612479979,-83.1005859375 43.068887774169625)")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
