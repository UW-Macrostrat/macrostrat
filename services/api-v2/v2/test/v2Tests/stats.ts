module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/api/v2/stats")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.metadata)
      .expect(validators.json)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should show ALL THE STATS", function (done) {
    request(settings.host)
      .get("/api/v2/stats?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output the stats in CSV", function (done) {
    request(settings.host)
      .get("/api/v2/stats?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });
};
