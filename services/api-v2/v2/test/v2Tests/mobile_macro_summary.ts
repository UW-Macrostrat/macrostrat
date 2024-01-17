module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/api/v2/mobile/macro_summary")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function (done) {
    request(settings.host)
      .get("/api/v2/mobile/macro_summary?lat=43.0706192&lng=-89.406167")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res) {
        var response = res.body.success.data;
        if (
          !response.lith.length ||
          !response.environ.length ||
          !response.econs.length ||
          !response.strat_names.length ||
          !response.strat_name_ids.length
        ) {
          throw new Error("Bad response");
        }
      })
      .end(function (error, res) {
        if (error) return done(error);
        done();
      });
  });
};
