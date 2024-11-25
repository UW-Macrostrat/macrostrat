  var request = require("supertest"),
    validators = require("../validators"),
    settings = require("../settings");
  //TODO need to modify these tests to work with the tileserver api
  it("should return a tile for original", function (done) {
    request(settings.host)
      .get("/maps/burwell/3/2/4/tile.png")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.tile)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a tile for vanilla", function (done) {
    request(settings.host)
      .get("/maps/burwell/vanilla/3/2/4/tile.png")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.tile)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

  it("should return a tile for emphasized", function (done) {
    request(settings.host)
      .get("/maps/burwell/emphasized/3/2/4/tile.png")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.tile)
      .end(function (error: any, res: any) {
        if (error) return done(error);
        done();
      });
  });

