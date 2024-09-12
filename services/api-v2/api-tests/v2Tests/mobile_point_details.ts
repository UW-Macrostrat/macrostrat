  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/mobile/point_details")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
/*
  it("should accept a lat and lng", function (done) {
    request(settings.host)
      .get("/mobile/point_details?lat=43&lng=-89")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: { gmus: any; }[]; }; }; }) {
        if (
          !res.body.success.data[0].gmus
        ) {
          throw new Error("Response missing a data type");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_id and unit_id", function (done) {
    request(settings.host)
      .get("/mobile/point_details?col_id=187&unit_id=184506")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: any) {
        if (
          !res.body.success.data[0].column ||
          !res.body.success.data[0].gmus
        ) {
          throw new Error("Response missing a data type");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

 */
