module.exports = function () {
  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");

  it("should return available routes", function (done) {
    request(settings.host)
      .get("/defs")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function (res: { body: { success: { routes: string | any[]; }; }; }) {
        if (res.body.success.routes.length < 5) {
          throw new Error("Wrong number of definition routes");
        }
      })
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });
};
