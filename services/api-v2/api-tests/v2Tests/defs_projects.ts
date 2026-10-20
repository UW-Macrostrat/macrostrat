var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", function (done) {
  request(settings.host)
    .get("/defs/projects")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.metadata)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should return a sample", function (done) {
    this.timeout(10000);
    request(settings.host)
    .get("/defs/projects?sample")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.projectSample)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should return all projects", function (done) {
    this.timeout(10000);
    request(settings.host)
    .get("/defs/projects?all")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should output CSV", function (done) {
    this.timeout(10000);
    request(settings.host)
    .get("/defs/projects?all&format=csv")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.csv)
    .expect("Content-Type", "text/csv; charset=utf-8")
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
