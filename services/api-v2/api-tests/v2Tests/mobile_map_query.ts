module.exports = function () {
  var request = require("supertest");
  var validators = require("../validators");
  var settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/mobile/map_query")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude, longitude, and z", function (done) {
    request(settings.host)
      .get("/mobile/map_query?lat=43.0706192&lng=-89.406167&z=8")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: any) {
        var response = res.body.success.data;
        if (!response.hasOwnProperty("elevation")) {
          throw new Error("Missing elevation from response");
        }
        if (!response.hasOwnProperty("burwell")) {
          throw new Error("Missing burwell from response");
        }
        if (!response.hasOwnProperty("macrostrat")) {
          throw new Error("Missing macrostrata from response");
        }
        if (!response.hasOwnProperty("lines")) {
          throw new Error("Missing lines from response");
        }
        if (!response.burwell.length) {
          throw new Error("Bad response");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should require a lat, lng, and z", function (done) {
    request(settings.host)
      .get("/mobile/map_query?lat=1&lng=1")
      .expect(validators.json)
      .expect(function (res: { statusCode: any; body: { hasOwnProperty: (arg0: string) => any; }; }) {
        //  var response = res.body.success.data
        if (res.statusCode != 400) {
          throw new Error("Wrong status code");
        }
        if (!res.body.hasOwnProperty("error")) {
          throw new Error("No error returned when one was expected");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should not choke on a fractional zoom", function (done) {
    request(settings.host)
      .get(
        "/mobile/map_query?lat=43.0706192&lng=-89.406167&z=8.984324234",
      )
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: any) {
        var response = res.body.success.data;
        if (!response.hasOwnProperty("elevation")) {
          throw new Error("Missing elevation from response");
        }
        if (!response.hasOwnProperty("burwell")) {
          throw new Error("Missing burwell from response");
        }
        if (!response.hasOwnProperty("macrostrat")) {
          throw new Error("Missing macrostrata from response");
        }
        if (!response.hasOwnProperty("lines")) {
          throw new Error("Missing lines from response");
        }
        if (!response.burwell.length) {
          throw new Error("Bad response");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
};
