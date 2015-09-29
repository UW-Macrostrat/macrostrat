module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return metadata", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function(done) {
    this.timeout(3000);
    
    request(settings.host)
      .get("/api/v1/geologic_units?lat=43&lng=-89.3&type=gmna")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a time interval name on GMUS", function(done) {
    this.timeout(5000);

    request(settings.host)
      .get("/api/v1/geologic_units?interval_name=Pliocene&type=gmus")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a time interval name on GMNA", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units?interval_name=Permian&type=gmna")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a unit name on GMUS", function(done) {
    this.timeout(4000);

    request(settings.host)
      .get("/api/v1/geologic_units?unit_name=Mancos%20Shale&type=gmus")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return geometry when asked", function(done) {
    request(settings.host)
      .get("/api/v1/geologic_units?lat=43&lng=-89.3&type=gmna&format=geojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
