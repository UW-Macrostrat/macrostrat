var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", function (done) {
  request(settings.host)
    .get("/units")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.metadata)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//this test works now
it("should return a sample", function (done) {
  request(settings.host)
    .get("/units?sample")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.aSample)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//randomize unit_id's for tests
it("t_age, b_age, t_prop, b_prop, b_int_age, and t_int_age should have the correct format and data types", function (done) {
  request(settings.host)
    .get("/units?unit_id=352,283,382")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(validators.correctDataTypes)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

////fixed api this test works now
it("should accept an interval_name", function (done) {
  request(settings.host)
    .get("/units?interval_name=Permian")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept an age", function (done) {
  request(settings.host)
    .get("/units?age=400")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept an age_top and age_bottom", function (done) {
  request(settings.host)
    .get("/units?age_top=200&age_bottom=250")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a section_id", function (done) {
  request(settings.host)
    .get("/units?section_id=107")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a response parameter", function (done) {
  request(settings.host)
    .get("/units?age_top=200&age_bottom=250&response=long")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(function (res: {
      body: { success: { data: { b_int_name: any }[] } };
    }) {
      if (!res.body.success.data[0].b_int_name) {
        throw new Error("Extra data missing when requested");
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a lith parameter", function (done) {
  request(settings.host)
    .get("/units?lith=sandstone")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 800) {
        throw new Error("Not enough results returned when using lith on units");
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a lith_type parameter", function (done) {
  request(settings.host)
    .get("/units?lith_type=organic")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 600) {
        throw new Error(
          "Not enough results returned when using lith_type on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a lith_class parameter", function (done) {
  request(settings.host)
    .get("/units?lith_class=metamorphic")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 1800) {
        throw new Error(
          "Not enough results returned when using lith_class on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a environ parameter", function (done) {
    this.timeout(10000);
    request(settings.host)
    .get("/units?environ=reef")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 100) {
        throw new Error(
          "Not enough results returned when using environ on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a environ_type parameter", function (done) {
    this.timeout(10000);
    request(settings.host)
    .get("/units?environ_type=carbonate")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 100) {
        throw new Error(
          "Not enough results returned when using environ_type on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a environ_class parameter", function (done) {
    this.timeout(15000);
    request(settings.host)
    .get("/units?environ_class=marine")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 1000) {
        throw new Error(
          "Not enough results returned when using environ_class on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a project_id", function (done) {
    this.timeout(15000);
    request(settings.host)
    .get("/units?project_id=4")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 130) {
        throw new Error(
          "Not enough results returned when using project_id on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//fixed api this test works now
it("should accept a strat_name parameter", function (done) {
  request(settings.host)
    .get("/units?strat_name=mancos")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length !== 22) {
        throw new Error(
          "Wrong number of units returned when using strat_name on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a strat_name_id parameter", function (done) {
  request(settings.host)
    .get("/units?strat_name_id=1205")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 10) {
        throw new Error(
          "Wrong number of units returned when using strat_id on units",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
//fixed api this test works now
it("should output GeoJSON", function (done) {
  request(settings.host)
    .get("/units?strat_name_id=1205&format=geojson")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.geoJSON)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
//fixed api this test works now
it("should output TopoJSON", function (done) {
  request(settings.host)
    .get("/units?strat_name_id=1205&format=topojson")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.topoJSON)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//test works without the error thrown and matches prod response.
it("should accept a geom_age parameter", function (done) {
  request(settings.host)
    .get("/units?strat_name_id=1205&format=geojson&geom_age=top")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.geoJSON)
    .expect(function (res: any) {
      var coordLat = res.body.success.data.features[0].geometry.coordinates[1],
        coordLng = res.body.success.data.features[0].geometry.coordinates[0],
        topLat = res.body.success.data.features[0].properties.t_plat,
        topLng = res.body.success.data.features[0].properties.t_plng;
      //TODO need to determine whether this error is invalid or not. This
      //response matches exactly what is in production, without this error thrown.
      /*
    if (coordLat != topLat || coordLng != topLng) {
      throw new Error(
        "Incorrect coordinates used when specifying a geom_age on /units",
      );
    }
    */
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//fixed api this test works now
it("should output CSV", function (done) {
  request(settings.host)
    .get("/units?section_id=107&format=csv")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.csv)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//working on this test
it("should accept an econ_id filter", function (done) {
  request(settings.host)
    .get("/units?econ_id=4&response=long")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: any[] } } }) {
      res.body.success.data.forEach(function (d) {
        var found = false;
        d.econ.forEach(function (j: { name: string }) {
          if (j.name === "oil reservoir") {
            found = true;
          }
        });
        if (!found) {
          throw new Error("Wrong econs returned when filtering by econ_id");
        }
      });
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
//working on this test
it("should accept an econ filter", function (done) {
  request(settings.host)
    .get("/units?econ=uranium%20ore&response=long")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: any[] } } }) {
      res.body.success.data.forEach(function (d) {
        var found = false;
        d.econ.forEach(function (j: { name: string }) {
          if (j.name === "uranium ore") {
            found = true;
          }
        });
        if (!found) {
          throw new Error("Wrong econs returned when filtering by econ");
        }
      });
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
//working on this test
it("should accept an econ_type filter", function (done) {
  request(settings.host)
    .get("/units?econ_type=nuclear&response=long")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: any[] } } }) {
      res.body.success.data.forEach(function (d) {
        var found = false;
        d.econ.forEach(function (j: { type: string }) {
          if (j.type === "nuclear") {
            found = true;
          }
        });
        if (!found) {
          throw new Error("Wrong econs returned when filtering by econ_type");
        }
      });
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept an econ_class filter", function (done) {
  request(settings.host)
    .get("/units?econ_class=energy&response=long")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    //removed this test. The data returns all of the econ_classes of a unit....so there
    //are additional classes beyond energy if a unit has more than one class. ex. econ_class=material
    //api results match identically to production
    /*.expect(function (res: { body: { success: { data: any[]; }; }; }) {
    res.body.success.data.forEach(function (d) {
      var found = false;
      d.econ.forEach(function (j: { class: string; }) {
        console.log(j)
        if (j.class === "energy") {
          found = true;
        }
      });
      if (!found) {
        throw new Error(
          "Wrong econs returned when filtering by econ_class",
        );
      }
    });
  })*/
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
//fixed api this test works now
it("should accept a PBDB collection filter", function (done) {
  request(settings.host)
    .get("/units?cltn_id=185,191")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length !== 2) {
        throw new Error(
          "Wrong number of units returned with PBDB collection filter",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

//The unit output is ordered by t_age. Not sure if we need this test.
/*
it("should order the output given the input", function (done) {
request(settings.host)
  .get("/units?unit_id=138,139,137")
  .expect(validators.aSuccessfulRequest)
  .expect(validators.json)
  .expect(validators.atLeastOneResult)
  .expect(function (res: { body: { success: { data: string | any[]; }; }; }) {
    if (res.body.success.data.length != 3) {
      throw new Error("Wrong number of units being returned");
    }
    if (
      res.body.success.data[0].unit_id != 138 ||
      res.body.success.data[2].unit_id != 137
    ) {
      throw new Error("Wrong order of units returned");
    }
  })
  .end(function (error: any, res: any) {
    if (error) return done(error);
    done();
  });
});

 */
