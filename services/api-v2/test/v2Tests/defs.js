module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return available routes", function(done) {
    request(settings.host)
      .get("/api/v1/defs")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function(res) {
        if (res.body.success.routes.length < 5) {
          throw new Error("Wrong number of definition routes")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
