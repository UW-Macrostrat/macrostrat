var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", function (done) {
  request(settings.host)
    .get("/defs/strat_names")
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
    .get("/defs/strat_names?sample")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.aSample)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a strat id", function (done) {
  request(settings.host)
    .get("/defs/strat_names?strat_name_id=1")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept multiple strat ids", function (done) {
  request(settings.host)
    .get("/defs/strat_names?strat_name_id=2188,7145")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length != 2) {
        throw new Error(
          "defs/strat_names does not return two results as expected",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a strat name", function (done) {
  request(settings.host)
    .get("/defs/strat_names?strat_name=Abercrombie")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a strat rank", function (done) {
  request(settings.host)
    .get("/defs/strat_names?rank=Gp")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should return all strat names", function (done) {
  this.timeout(10000);
  request(settings.host)
    .get("/defs/strat_names?all")
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
    .get("/defs/strat_names?strat_name=Abercrombie&format=csv")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.csv)
    .expect("Content-Type", "text/csv; charset=utf-8")
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept rule=all with a strat id", function (done) {
  request(settings.host)
    .get("/defs/strat_names?rule=all&strat_name_id=9992")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res) {
      const hasRequestedStratName = res.body.success.data.some(function (d) {
        return d.strat_name_id === 9992;
      });

      if (!hasRequestedStratName) {
        throw new Error(
          "defs/strat_names?rule=all&strat_name_id=9992 does not include the requested strat_name_id",
        );
      }
    })
    .end(function (error, res) {
      if (error) return done(error);
      done();
    });
});

it("should accept rule=down with a concept id", function (done) {
  request(settings.host)
    .get("/defs/strat_names?strat_name_id=9992")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error, res) {
      if (error) return done(error);

      const conceptId = res.body.success.data[0].concept_id;

      request(settings.host)
        .get("/defs/strat_names?rule=down&concept_id=" + conceptId)
        .expect(validators.aSuccessfulRequest)
        .expect(validators.json)
        .expect(validators.atLeastOneResult)
        .end(function (error, res) {
          if (error) return done(error);
          done();
        });
    });
});