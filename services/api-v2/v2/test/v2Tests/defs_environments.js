module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");
  
  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an environment class", function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments?environ_class=non-marine")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an environment type", function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments?environ_type=carbonate")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an environment", function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments?environ=open%20shallow%20subtidal")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an environment id", function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments?environ_id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all environment definitions", function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments?all")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return CSV", function(done) {
    request(settings.host)
      .get("/api/v2/defs/environments?all&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .expect("Content-Type", "text/csv; charset=utf-8")
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
