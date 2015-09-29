module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return metadata", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units/map")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should throw an error if a required parameter is ommitted", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units/map?interval_name=Permian")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a type and interval name", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units/map?interval_name=Permian&type=gmna")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output Topojson", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units/map?interval_name=Permian&type=gmna&format=topojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.topoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
