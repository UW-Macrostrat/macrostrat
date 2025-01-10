  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return metadata", function (done) {
    request(settings.host)
      .get("/mobile/macro_summary")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function (done) {
    this.timeout(10000);
    request(settings.host)
      .get("/mobile/macro_summary?lat=43.0706192&lng=-89.406167")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function (res: { body: { success: { data: any; }; }; }) {
        var response = res.body.success.data;
        if (
          !("lith" in response) ||
          !("environ" in response) ||
          !("econs" in response) ||
          !("strat_names" in response) ||
          !("strat_name_ids" in response)
        ) {
          throw new Error("Missing expected keys in response");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
