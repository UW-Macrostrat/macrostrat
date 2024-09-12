  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/defs/lithologies")
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
      .get("/defs/lithologies?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith_id", function (done) {
    request(settings.host)
      .get("/defs/lithologies?lith_id=3")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length !== 1) {
          throw new Error(
            "Should have returned 1 lith definition but returned more or less",
          );
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept multiple lith_ids", function (done) {
    request(settings.host)
      .get("/defs/lithologies?lith_id=3,4,5")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length !== 3) {
          throw new Error(
            "Should have returned 3 lith definitions but returned more or less",
          );
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith class", function (done) {
    request(settings.host)
      .get("/defs/lithologies?lith_class=sedimentary")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should show all lith definitions when asked", function (done) {
    request(settings.host)
      .get("/defs/lithologies?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length < 2) {
          throw new Error("Should have returned more than 2 lith_definitions");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should output CSV", function (done) {
    request(settings.host)
      .get("/defs/lithologies?lith_id=3&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
