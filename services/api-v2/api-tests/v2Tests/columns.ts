var request = require("supertest"),
validators = require("../validators"),
settings = require("../settings");

it("should return metadata", function (done) {
request(settings.host)
  .get("/columns")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.metadata)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

//Fixed this test to work on dev and local
it("should return a sample", function (done) {
request(settings.host)
  .get("/columns?sample")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.aSample)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

//Fixed this test to work on dev and local
it("should accept an interval name", function (done) {
request(settings.host)
  .get("/columns?interval_name=Permian")
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
  .get("/columns?age=271")
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
  .get("/columns?age_top=200&age_bottom=250")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

//fixed test in dev and it is now working.
it("should accept a strat_name parameter", function (done) {
request(settings.host)
  .get("/columns?strat_name=mancos")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should accept a strat_name_id parameter", function (done) {
request(settings.host)
  .get("/columns?strat_name_id=1205")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});


//Checking to see if the rest of the tests below work in prod.
//count for max number of columns ~50?
it("should accept a latitude and longitude", function (done) {
request(settings.host)
  .get("/columns?lat=43.3&lng=-89.3")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .expect(function (res: { body: { success: { data: { col_id: number; }[]; }; }; }) {
    if (res.body.success.data[0].col_id != 187) {
      throw new Error("Columns returning the wrong column for the lat/lng");
    }
  })
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should return topojson", function (done) {
request(settings.host)
  .get("/columns?age=2&format=topojson")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.topoJSON)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should return csv", function (done) {
request(settings.host)
  .get("/columns?age=2&format=csv")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.csv)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});


it("should accept a project_id", function (done) {
  this.timeout(7000);
request(settings.host)
  .get("/columns?project_id=4")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

it("should accept a lat/lng and return all adjacent columns", function (done) {
    request(settings.host)
  .get("/columns?lat=43.3&lng=-89.3&adjacents=true")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
    if (res.body.success.data.length != 6) {
      throw new Error("Wrong number of adjacent columns being returned");
    }
  })
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

