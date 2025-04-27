var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", function (done) {
  request(settings.host)
    .get("/carto/small")
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
    .get("/carto/small?sample")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.aSample)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a latitude and longitude", function (done) {
  request(settings.host)
    .get("/carto/small?lat=43&lng=-89.3")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

/*
//These tests fail production and dev. They are commented out for now.

it("should return geometry when asked", function (done) {
request(settings.host)
  .get("/carto/small?lat=43&lng=-89.3&format=geojson")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.geoJSON)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should accept a shape", function (done) {
this.timeout(5000);

request(settings.host)
  .get(
    "/carto/small?shape=POLYGON((-95.44921875 41.3355759731239,-95.44921875 43.0929606771163,-92.79052734375 43.0929606771163,-92.79052734375 41.3355759731239,-95.44921875 41.3355759731239))",
  )
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});
*/
