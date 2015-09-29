module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return metadata", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/burwell")
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
      .get("/api/v2/geologic_units/burwell?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/burwell?lat=43&lng=-89.3&scale=large")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a map_id", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/burwell?map_id=605211&scale=medium")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept multiple map_ids", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/burwell?map_id=605211,605210,605209&scale=medium")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length != 3) {
          throw new Error("Wrong number of features returned with multiple map_ids");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat_name_id", function(done) {
    request(settings.host)
      .get("/api/v2/geologic_units/burwell?strat_name_id=1205&scale=medium")
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
      .get("/api/v2/geologic_units/burwell?unit_id=6124&scale=medium")
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
      .get("/api/v2/geologic_units/burwell?lat=43&lng=-89.3&format=geojson&scale=medium")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

}
