  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/fossils")
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
      .get("/fossils?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a time_interval", function (done) {
    this.timeout(4000);

    request(settings.host)
      .get("/fossils?interval_name=Permian")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an age", function (done) {
    request(settings.host)
      .get("/fossils?age=123")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an age_top and age_bottom", function (done) {
    request(settings.host)
      .get("/fossils?age_top=100&age_bottom=120")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_id", function (done) {
    request(settings.host)
      .get("/fossils?col_id=446")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept multiple col_ids", function (done) {
    request(settings.host)
      .get("/fossils?col_id=446,56")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length < 29) {
          throw new Error(
            "Wrong number of fossil collections returned with multiple IDs supplied",
          );
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept one or more unit_ids", function (done) {
    request(settings.host)
      .get("/fossils?unit_id=14777,14949,15018,15211,15210")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should output Topojson", function (done) {
    request(settings.host)
      .get("/fossils?interval_name=Permian&format=topojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.topoJSON)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
