  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return a list of all visible routes", function (done) {
    request(settings.host)
      .get("")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
