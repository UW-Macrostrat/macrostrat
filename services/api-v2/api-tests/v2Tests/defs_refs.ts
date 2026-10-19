var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", function (done) {
  request(settings.host)
    .get("/defs/refs")
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
    .get("/defs/refs?sample")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.aSample)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should return all refs", function (done) {
  request(settings.host)
    .get("/defs/refs?all")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a ref_id", function (done) {
  request(settings.host)
    .get("/defs/refs?ref_id=1,2,3")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length !== 3) {
        throw new Error(
          "Should have returned 3 ref definitions but returned more or less",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should output CSV", function (done) {
  request(settings.host)
    .get("/defs/refs?all&format=csv")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.csv)
    .expect("Content-Type", "text/csv; charset=utf-8")
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
