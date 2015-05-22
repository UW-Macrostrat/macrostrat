module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v2/columns")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an interval name", function(done) {
    request(settings.host)
      .get("/api/v2/columns?interval_name=Permian")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an age", function(done) {
    request(settings.host)
      .get("/api/v2/columns?age=271")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an age_top and age_bottom", function(done) {
    request(settings.host)
      .get("/api/v2/columns?age_top=200&age_bottom=250")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat_name parameter", function(done) {
    request(settings.host)
      .get("/api/v2/columns?strat_name=mancos")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat_id parameter", function(done) {
    request(settings.host)
      .get("/api/v2/columns?strat_id=1205")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });


  it("should return topojson", function(done) {
    request(settings.host)
      .get("/api/v2/columns?age=2&format=topojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.topoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return csv", function(done) {
    request(settings.host)
      .get("/api/v2/columns?age=2&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a latitude and longitude", function(done) {
    request(settings.host)
      .get("/api/v2/columns?lat=43.3&lng=-89.3")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data[0].col_id != 187) {
          throw new Error("Columns returning the wrong column for the lat/lng");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a project_id", function(done) {
    request(settings.host)
      .get("/api/v2/columns?project_id=4")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lat/lng and return all adjacent columns", function(done) {
    request(settings.host)
      .get("/api/v2/columns?lat=43.3&lng=-89.3&adjacents=true")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length != 6) {
          throw new Error("Wrong number of adjacent columns being returned");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
