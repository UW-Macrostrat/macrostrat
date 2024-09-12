  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/defs/columns")
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
      .get("/defs/columns?sample")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.aSample)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_group_id", function (done) {
    request(settings.host)
      .get("/defs/columns?col_group_id=17")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept multiple col_group_ids", function (done) {
    request(settings.host)
      .get("/defs/columns?col_group_id=17,18")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length < 60) {
          throw new Error(
            "Wrong number of columns returned with multiple col_group_ids",
          );
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_id", function (done) {
    request(settings.host)
      .get("/defs/columns?col_id=17")
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
      .get("/defs/columns?col_id=3,4")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length !== 2) {
          throw new Error(
            "Wrong number of columns returned with multiple col_ids",
          );
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_name", function (done) {
    request(settings.host)
      .get("/defs/columns?col_name=Eastern%20Kentucky")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all columns", function (done) {
    request(settings.host)
      .get("/defs/columns?id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
        if (res.body.success.data.length < 1500) {
          throw new Error("Not enough results returned on defs/columns");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
