  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/defs/measurements")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a sample", function (done) {
    this.timeout(5000);
    request(settings.host)
      .get("/defs/measurements?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept measurement IDs", function (done) {
    request(settings.host)
      .get("/defs/measurements?measure_id=3,4")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length !== 2) {
          throw new Error("Should have returned 2 measurements but did not");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a measurement class", function (done) {
    this.timeout(9000);
    request(settings.host)
      .get("/defs/measurements?measurement_class=geochemical")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: any[]; }; }; }) {
        res.body.success.data.forEach(function (d) {
          if (d.class != "geochemical") {
            throw new Error("Wrong measurement class returned");
          }
        })
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });


  it("should accept a measurement type", function (done) {
    this.timeout(5000);
    request(settings.host)
      .get("/defs/measurements?measurement_type=geochronological")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: any[]; }; }; }) {
        res.body.success.data.forEach(function (d) {
          if (d.type != "geochronological") {
            throw new Error("Wrong measurement type returned");
          }
        });
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });


  it("should return all definitions", function (done) {
    this.timeout(5000);
    request(settings.host)
      .get("/defs/measurements?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return CSV", function (done) {
    request(settings.host)
      .get(
        "/defs/measurements?measurement_type=geochronological&format=csv",
      )
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
