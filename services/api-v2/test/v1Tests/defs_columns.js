module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v1/defs/columns")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_group_id", function(done) {
    request(settings.host)
      .get("/api/v1/defs/columns?col_group_id=17")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_id", function(done) {
    request(settings.host)
      .get("/api/v1/defs/columns?col_id=17")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a col_name", function(done) {
    request(settings.host)
      .get("/api/v1/defs/columns?col_name=Eastern%20Kentucky")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return all columns", function(done) {
    request(settings.host)
      .get("/api/v1/defs/columns?id=1")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 1500) {
          throw new Error("Not enough results returned on defs/columns");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
