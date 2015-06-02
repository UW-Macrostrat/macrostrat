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

  it("should accept a search", function(done) {
    this.timeout(4000);

    request(settings.host)
      .get("/api/v2/geologic_units/gmus?search=Mancos%20Shale")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a unit_link", function(done) {
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


  it("should accept a unit_id", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/gmus?unit_id=2470,38484")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });


  it("should accept a strat_name_id", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/gmus?strat_name_id=1205")
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
