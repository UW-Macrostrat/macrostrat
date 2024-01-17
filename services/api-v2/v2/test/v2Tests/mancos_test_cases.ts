module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it("should return point data for Detroit", function(done) {
    request(settings.host)
      .get("/api/v2/mobile/point?lat=42.331427&lng=-83.045754")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function(res) {
        if (res.body.success.data.uid !== 1114738) {
          throw new Error("Wrong unit returned for Detroit")
        }
        if (res.body.success.data.rocktype.length < 2) {
          throw new Error("Invalid rocktypes returned for Detroit")
        }
        if (res.body.success.data.age !== "Middle Devonian") {
          throw new Error("Invalid age returned for Detroit")
        }
        if (res.body.success.data.name.length < 2 || res.body.success.data.desc.length < 2 || res.body.success.data.comm.length < 2) {
          throw new Error("Invalid data returned for Detroit")
        }
        if (res.body.success.data.strat_unit.length > 0) {
          throw new Error("Invalid strat unit returned for Detroit")
        }
        if (res.body.success.data.col_id !== 1594) {
          throw new Error("Invalid column returned for Detroit")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return point details for Detroit", function(done) {
    request(settings.host)
      .get("/api/v2/mobile/point_details?lat=42.331427&lng=-83.045754")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (!res.body.success.data[0].column || !res.body.success.data[0].gmus) {
          throw new Error("Missing details for Detroit")
        }
        if (res.body.success.data[0].column.units.length < 5) {
          throw new Error("Missing units from details for Detroit")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return point data for Toronto", function(done) {
    request(settings.host)
      .get("/api/v2/mobile/point?lat=43.651893&lng=-79.381713")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function(res) {
        if (res.body.success.data.uid !== 619176) {
          throw new Error("Wrong unit returned for Toronto")
        }
        if (res.body.success.data.rocktype.length < 1) {
          throw new Error("Invalid rocktypes returned for Toronto")
        }
        if (res.body.success.data.age !== "Late Ordovician") {
          throw new Error("Invalid age returned for Toronto")
        }
        if (res.body.success.data.name.length < 2) {
          throw new Error("Invalid data returned for Toronto")
        }
        if (res.body.success.data.strat_unit.length > 0 || res.body.success.data.desc.length > 0 || res.body.success.data.comm.length > 0) {
          throw new Error("Invalid data returned for Toronto")
        }
        if (res.body.success.data.col_id !== 1598) {
          throw new Error("Invalid column returned for Toronto")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return point details for Toronto", function(done) {
    request(settings.host)
      .get("/api/v2/mobile/point_details?lat=43.651893&lng=-79.381713")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (!res.body.success.data[0].column) {
          throw new Error("Missing details for Toronto")
        }
        if (res.body.success.data[0].column.units.length < 5) {
          throw new Error("Missing units from details for Toronto")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return point data for Buenos Aires", function(done) {
    request(settings.host)
      .get("/api/v2/mobile/point?lat=-34.565383&lng=-58.452759")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function(res) {
        if (res.body.success.data.uid.length > 0) {
          throw new Error("Wrong unit returned for Buenos Aires")
        }
        if (res.body.success.data.rocktype.length > 0) {
          throw new Error("Invalid rocktypes returned for Buenos Aires")
        }
        if (res.body.success.data.age.length > 0) {
          throw new Error("Invalid age returned for Buenos Aires")
        }
        if (res.body.success.data.name.length > 0) {
          throw new Error("Invalid data returned for Buenos Aires")
        }
        if (res.body.success.data.strat_unit.length > 0 || res.body.success.data.desc.length > 0 || res.body.success.data.comm.length > 0) {
          throw new Error("Invalid data returned for Buenos Aires")
        }
        if (res.body.success.data.col_id.length > 0) {
          throw new Error("Invalid column returned for Buenos Aires")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should return point details for Buenos Aires", function(done) {
    request(settings.host)
      .get("/api/v2/mobile/point_details?lat=-34.565383&lng=-58.452759")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (!res.body.success.data[0].column) {
          throw new Error("Missing empty column for Buenos Aires")
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
