module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/defs/lithology_attributes")
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
      .get("/defs/lithology_attributes?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an att_type", function (done) {
    request(settings.host)
      .get("/defs/lithology_attributes?att_type=bedform")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith_att", function (done) {
    request(settings.host)
      .get("/defs/lithology_attributes?lith_att=mounds")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith_att_id", function (done) {
    request(settings.host)
      .get("/defs/lithology_attributes?lith_att_id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept multiple lith_att_ids", function (done) {
    request(settings.host)
      .get("/defs/lithology_attributes?lith_att_id=3,4,5")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length !== 3) {
          throw new Error(
            "Should have returned 3 lithology attribute definitions but returned more or less",
          );
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all records", function (done) {
    request(settings.host)
      .get("/defs/lithology_attributes?all")
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
      .get("/defs/lithology_attributes?lith_att=mounds&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
};
