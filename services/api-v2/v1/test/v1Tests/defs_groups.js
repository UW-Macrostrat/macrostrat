module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");
 
  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v1/defs/groups")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all column groups", function(done) {
    request(settings.host)
      .get("/api/v1/defs/groups?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output CSV", function(done) {
    request(settings.host)
      .get("/api/v1/defs/groups?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
