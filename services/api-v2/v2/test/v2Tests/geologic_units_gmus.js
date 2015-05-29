module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return metadata", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/gmus")
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
      .get("/api/v2/geologic_units/gmus?lat=43&lng=-89.3")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a time interval_name", function(done) {
    this.timeout(5000);

    request(settings.host)
      .get("/api/v2/geologic_units/gmus?interval_name=Pliocene")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a unit_name", function(done) {
    this.timeout(4000);

    request(settings.host)
      .get("/api/v2/geologic_units/gmus?unit_name=Mancos%20Shale")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a unit_link", function(done) {
    this.timeout(4000);

    request(settings.host)
      .get("/api/v2/geologic_units/gmus?unit_link=WIOp;0")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a GID", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/gmus?gid=184506")
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
      .get("/api/v2/geologic_units/gmus?lat=43&lng=-89.3&format=geojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
