  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/defs/sources")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a sample", function (done) {
    request(settings.host)
      .get("/defs/sources?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all sources", function (done) {
    request(settings.host)
      .get("/defs/sources?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should output CSV", function (done) {
    request(settings.host)
      .get("/defs/sources?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a source_id", function (done) {
    request(settings.host)
      .get("/defs/sources?source_id=1,2")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length != 2) {
          throw new Error("Wrong number of sources returned with source_id");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all sources as GeoJSON", function(done) {
    request(settings.host)
      .get("/defs/sources?all&format=geojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function(error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });


  it("should accept a scale", function (done) {
    request(settings.host)
      .get("/defs/sources?scale=medium")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: any[]; }; }; }) {
        res.body.success.data.forEach(function (d) {
          if (d.scale != "medium") {
            throw new Error("Wrong scale returned when filtering by scale");
          }
        });
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function (done) {
    request(settings.host)
      .get("/defs/sources?lat=43&lng=-89")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a WKT shape", function (done) {
    request(settings.host)
      .get(
        "/defs/sources?shape=LINESTRING(-122.3438%2037,-89.3527%2043.0582)&buffer=100",
      )
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
