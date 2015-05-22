module.exports = function() {
  var request = require("supertest"),
      validators = require("../validators"),
      settings = require("../settings");

  it('should return metadata', function(done) {
    request(settings.host)
      .get("/api/v1/units")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.metadata)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept an interval_name", function(done) {
    request(settings.host)
      .get("/api/v1/units?interval_name=Permian")
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
      .get("/api/v1/units?age=400")
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
      .get("/api/v1/units?age_top=200&age_bottom=250")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a section_id", function(done) {
    request(settings.host)
      .get("/api/v1/units?section_id=107")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a response parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?age_top=200&age_bottom=250&response=long")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(function(res) {
        if (!res.body.success.data[0].LO_interval) {
          throw new Error("Extra data missing when requested");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?lith=sandstone")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 800) {
          throw new Error("Not enough results returned when using lith on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith_type parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?lith_type=carbonate")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 11000) {
          throw new Error("Not enough results returned when using lith_type on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a lith_class parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?lith_class=metamorphic")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 1800) {
          throw new Error("Not enough results returned when using lith_class on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });


  it("should accept a environ parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?environ=marine indet.")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 100) {
          throw new Error("Not enough results returned when using environ on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a environ_type parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?environ_type=carbonate")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 100) {
          throw new Error("Not enough results returned when using environ_type on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a environ_class parameter", function(done) {
    this.timeout(5000);

    request(settings.host)
      .get("/api/v1/units?environ_class=marine")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 1000) {
          throw new Error("Not enough results returned when using environ_class on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });


  it("should accept a project_id", function(done) {
    request(settings.host)
      .get("/api/v1/units?project_id=4")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length < 130) {
          throw new Error("Not enough results returned when using project_id on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });


  it("should accept a strat_name parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?strat_name=mancos")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length !== 22) {
          throw new Error("Wrong number of units returned when using strat_name on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a strat_id parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?strat_id=1205,4260")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length !== 31) {
          throw new Error("Wrong number of units returned when using strat_id on units");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output GeoJSON", function(done) {
    request(settings.host)
      .get("/api/v1/units?strat_id=1205&format=geojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output TopoJSON", function(done) {
    request(settings.host)
      .get("/api/v1/units?strat_id=1205&format=topojson")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.topoJSON)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should accept a geom_age parameter", function(done) {
    request(settings.host)
      .get("/api/v1/units?strat_id=1205&format=geojson&geom_age=top")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.geoJSON)
      .expect(function(res) {
        var coordLat = res.body.success.data.features[0].geometry.coordinates[1],
            coordLng = res.body.success.data.features[0].geometry.coordinates[0],
            topLat = res.body.success.data.features[0].properties.t_plat,
            topLng  = res.body.success.data.features[0].properties.t_plng;

        if (coordLat != topLat || coordLng != topLng) {
          throw new Error("Incorrect coordinates used when specifying a geom_age on /units");
        }

      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should output CSV", function(done) {
    request(settings.host)
      .get("/api/v1/units?section_id=107&format=csv")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.csv)
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });

  it("should order the output given the input", function(done) {
    request(settings.host)
      .get("/api/v1/units?id=138,139,137")
      .expect(validators.aSuccessfulRequest)
      .expect(validators.json)
      .expect(validators.atLeastOneResult)
      .expect(function(res) {
        if (res.body.success.data.length != 3) {
          throw new Error("Wrong number of units being returned");
        }
        if (res.body.success.data[0].id != 138 || res.body.success.data[2].id != 137) {
          throw new Error("Wrong order of units returned");
        }
      })
      .end(function(error, res) {
        if (error) return done(error);
        done();
      });
  });
}
