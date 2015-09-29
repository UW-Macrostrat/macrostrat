module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v1/column")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it('should be able to use a column id', function(done) {
    request(settings.host)
      .get("/api/v1/column?id=17")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it('should be able to use a lat and lng', function(done) {
    request(settings.host)
      .get("/api/v1/column?lat=50&lng=-80")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it('should return geometry when asked', function(done) {
    request(settings.host)
      .get("/api/v1/column?id=17&geom=true")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it('should accept a long response output', function(done) {
    request(settings.host)
      .get("/api/v1/column?lat=50&lng=-80&response=long")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
