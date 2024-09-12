var request = require("supertest"),
validators = require("../validators"),
settings = require("../settings");

it("/defs/intervals should return metadata", function (done) {
request(settings.host)
  .get("/defs/intervals")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.metadata)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("/defs/intervals?sample should return a sample", function (done) {
request(settings.host)
  .get("/defs/intervals?sample")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.aSample)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});


//need to pass all other parameters through this test to ensure outputs are valid.
it("t_age and b_age should have the correct format and data types", function (done) {
request(settings.host)
  .get("/defs/intervals?id=366")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
    .expect(validators.correctDataTypes)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should accept a timescale parameter", function (done) {
request(settings.host)
  .get("/defs/intervals?timescale=new%20zealand%20ages")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should accept an interval id", function (done) {
request(settings.host)
  .get("/defs/intervals?id=366")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});


it("should return all definitions", function (done) {
request(settings.host)
  .get("/defs/intervals?all")
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
  .get("/defs/intervals?timescale=new%20zealand%20ages&format=csv")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.csv)
  .expect("Content-Type", "text/csv; charset=utf-8")
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should accept an early and late age", function (done) {
request(settings.host)
  .get("/defs/intervals?late_age=0&early_age=130")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it(" should accept an age", function (done) {
request(settings.host)
  .get("/defs/intervals?age=200")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});


it("should accept an interval_name", function (done) {
request(settings.host)
  .get("/intervals?interval_name=Permian")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});


