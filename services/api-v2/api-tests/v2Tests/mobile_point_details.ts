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

it("should accept a latitude and longitude", function (done) {
  request(settings.host)
    .get("/mobile/point_details?lat=33.91&lng=-83.37")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(isArrayResult)
    .expect(hasKeys("gmus", "column"))
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

function isArrayResult(res: any) {
  /** There is at least one result */
  const { data } = res.body.success;
  if (!Array.isArray(data)) {
    return false;
  }
  return data.length > 0;
}

function hasKeys(...expectedKeys: string[]) {
  return (res: any) => {
    const { data } = res.body.success;
    const result = data[0];
    return expectedKeys.every((key) => key in result);
  };
}

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
//TODO gmus table is failing

it("should accept a lat and lng", function (done) {
  request(settings.host)
    .get("/mobile/point_details?lat=43&lng=-89")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: { gmus: any }[] } } }) {
      if (!res.body.success.data[0].gmus) {
        throw new Error("Response missing a data type");
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//TODO: endpoint is failing because of the gmus error
/**
it("should accept a col_id and unit_id", function (done) {
  request(settings.host)
    .get("/mobile/point_details?col_id=187&unit_id=184506")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: any) {
      if (!res.body.success.data[0].column || !res.body.success.data[0].gmus) {
        throw new Error("Response missing a data type");
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
 */
