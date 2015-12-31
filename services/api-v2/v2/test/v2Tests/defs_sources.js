module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources")
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
      .get("/api/v2/defs/sources?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all sources", function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources?all")
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
      .get("/api/v2/defs/sources?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a source_id", function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources?source_id=1,2,3")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length != 3) {
          throw new Error("Wrong number of sources returned with source_id");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all sources as GeoJSON", function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources?all&format=geojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a scale", function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources?scale=medium")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        res.body.success.data.forEach(function(d) {
          if (d.scale != "medium") {
            throw new Error("Wrong scale returned when filtering by scale");
          }
        });
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources?lat=43&lng=-89")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a WKT shape", function(done) {
    request(settings.host)
      .get("/api/v2/defs/sources?shape=LINESTRING(-122.3438%2037,-89.3527%2043.0582)&buffer=100")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
