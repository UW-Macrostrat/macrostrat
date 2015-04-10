var assert = require("assert"),
    should = require("should"),
    request = require("supertest"),
    async = require("async");

var host = "http://localhost:5000";


function aSuccessfulRequest(res) {
  if (res.statusCode !== 200) {
    throw new Error("Bad status code");
  }
  if (res.headers["access-control-allow-origin"] !== "*") {
    throw new Error("Wrong access-control-allow-origin headers");
  }
}

function metadata(res) {
  // Make sure all the key metadata sections exist
  if (!res.body.success.description) {
    throw new Error("Route description missing");
  }
  if (!res.body.success.options) {
    throw new Error("Route options missing");
  }
  if (!res.body.success.options.parameters) {
    throw new Error("Route parameters missing");
  }
  if (!res.body.success.options.output_formats) {
    throw new Error("Route output formats missing");
  }
  if (!res.body.success.options.examples) {
    throw new Error("Route examples missing");
  }
  if (!res.body.success.options.fields) {
    throw new Error("Route fields missing");
  }

  // Make sure the metadata sections are formatted properly
  if (!(res.body.success.options.parameters instanceof Object)) {
    throw new Error("Something wrong with parameters object");
  }
  if (!(res.body.success.options.output_formats instanceof Array)) {
    throw new Error("Something wrong with output formats array");
  }
  if (!(res.body.success.options.examples instanceof Array)) {
    throw new Error("Something wrong with examples array");
  }
  if (!(res.body.success.options.fields instanceof Object)) {
    throw new Error("Something wrong with fields object");
  }

  // Make sure metadata sections are populated
  if (Object.keys(res.body.success.options.parameters).length < 1) {
    throw new Error("Route is missing parameters");
  }
  if (res.body.success.options.output_formats.length < 1) {
    throw new Error("Route is missing output formats");
  }
  if (res.body.success.options.examples.length < 1) {
    throw new Error("Route is missing examples");
  }
  if (Object.keys(res.body.success.options.fields).length < 1) {
    throw new Error("Route is missing field definitions");
  }
}

function geoJSON(res) {
  if(res.body.success.data.type !== "FeatureCollection") {
    throw new Error("GeoJSON was not returned");
  }
}

function topoJSON(res) {
  if(res.body.success.data.type !== "Topology") {
    throw new Error("TopoJSON was not returned");
  }
}

function json(res) {
  if (!res.body.success && !res.body.error) {
    throw new Error("Request did not return valid JSON");
  }
}

function csv(res) {
  if (res.body.length < 10) {
    throw new Error("No CSV output recieved");
  }
}

function atLeastOneResult(res) {
  if (res.body.success.data.length < 1) {
    throw new Error("Should have returned at least one result");
  } 
}

describe('Version 1', function() {
/* Root route */
  describe('root', function() {
    it('should return a list of all visible routes', function(done) {
      request(host)
        .get("/api")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* column */
  describe("column", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/column")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it('should be able to use a column id', function(done) {
      request(host)
        .get("/api/column?id=17")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it('should be able to use a lat and lng', function(done) {
      request(host)
        .get("/api/column?lat=50&lng=-80")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it('should return geometry when asked', function(done) {
      request(host)
        .get("/api/column?id=17&geom=true")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it('should accept a long response output', function(done) {
      request(host)
        .get("/api/column?lat=50&lng=-80&response=long")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* columns */
  describe("columns", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/columns")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an interval name", function(done) {
      request(host)
        .get("/api/columns?interval_name=Permian")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age", function(done) {
      request(host)
        .get("/api/columns?age=271")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age_top and age_bottom", function(done) {
      request(host)
        .get("/api/columns?age_top=200&age_bottom=250")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a strat_name parameter", function(done) {
      request(host)
        .get("/api/columns?strat_name=mancos")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a strat_id parameter", function(done) {
      request(host)
        .get("/api/columns?strat_id=1205")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });


    it("should return topojson", function(done) {
      request(host)
        .get("/api/columns?age=2&format=topojson")
        .expect(aSuccessfulRequest)
        .expect(topoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return csv", function(done) {
      request(host)
        .get("/api/columns?age=2&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a latitude and longitude", function(done) {
      request(host)
        .get("/api/columns?lat=43.3&lng=-89.3")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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

    it("should accept a lat/lng and return all adjacent columns", function(done) {
      request(host)
        .get("/api/columns?lat=43.3&lng=-89.3&adjacents=true")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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

  });

/* sections */
  describe("sections", function() {
    it("should return metadata", function(done) {
      request(host)
        .get("/api/sections")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all sections", function(done) {
      this.timeout(6000);

      request(host)
        .get("/api/sections?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a column id", function(done) {
      request(host)
        .get("/api/sections?col_id=49")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return csv", function(done) {
      request(host)
        .get("/api/sections?col_id=17&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* units */
  describe("units", function() {

    it('should return metadata', function(done) {
      request(host)
        .get("/api/units")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an interval_name", function(done) {
      request(host)
        .get("/api/units?interval_name=Permian")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age", function(done) {
      request(host)
        .get("/api/units?age=400")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age_top and age_bottom", function(done) {
      request(host)
        .get("/api/units?age_top=200&age_bottom=250")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a section_id", function(done) {
      request(host)
        .get("/api/units?section_id=107")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a response parameter", function(done) {
      request(host)
        .get("/api/units?age_top=200&age_bottom=250&response=long")
        .expect(aSuccessfulRequest)
        .expect(json)
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
      request(host)
        .get("/api/units?lith=sandstone")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/units?lith_type=carbonate")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/units?lith_class=metamorphic")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/units?environ=marine indet.")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/units?environ_type=carbonate")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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

      request(host)
        .get("/api/units?environ_class=marine")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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

    it("should accept a strat_name parameter", function(done) {
      request(host)
        .get("/api/units?strat_name=mancos")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/units?strat_id=1205,4260")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/units?strat_id=1205&format=geojson")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output TopoJSON", function(done) {
      request(host)
        .get("/api/units?strat_id=1205&format=topojson")
        .expect(aSuccessfulRequest)
        .expect(topoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a geom_age parameter", function(done) {
      request(host)
        .get("/api/units?strat_id=1205&format=geojson&geom_age=top")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
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
      request(host)
        .get("/api/units?section_id=107&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should order the output given the input", function(done) {
      request(host)
        .get("/api/units?id=138,139,137")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
  });

/* fossils */
  describe("fossils", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/fossils")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a time_interval", function(done) {
      request(host)
        .get("/api/fossils?interval_name=Permian")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age", function(done) {
      request(host)
        .get("/api/fossils?age=123")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age_top and age_bottom", function(done) {
      request(host)
        .get("/api/fossils?age_top=100&age_bottom=120")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output Topojson", function(done) {
      request(host)
        .get("/api/fossils?interval_name=Permian&format=topojson")
        .expect(aSuccessfulRequest)
        .expect(topoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* stats */
  describe("stats", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/stats")
        .expect(aSuccessfulRequest)
        .expect(metadata)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should show ALL THE STATS", function(done) {
      request(host)
        .get("/api/stats?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output the stats in CSV", function(done) {
      request(host)
        .get("/api/stats?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("defs", function() {
    it("should return available routes", function(done) {
      request(host)
        .get("/api/defs")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(function(res) {
          if (res.body.success.routes.length < 5) {
            throw new Error("Wrong number of definition routes")
          }
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* defs/lithologies */
  describe("defs/lithologies", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/lithologies")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a lith id", function(done) {
      request(host)
        .get("/api/defs/lithologies?id=3")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(function(res) {
          if (res.body.success.data.length !== 1) {
            throw new Error("Should have returned 1 lith definition but returned more or less");
          } 
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a lith class", function(done) {
      request(host)
        .get("/api/defs/lithologies?lith_class=sedimentary")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should show all lith definitions when asked", function(done) {
      request(host)
        .get("/api/defs/lithologies?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(function(res) {
          if (res.body.success.data.length < 2) {
            throw new Error("Should have returned more than 2 lith_definitions");
          } 
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/defs/lithologies?id=3&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* defs/lithology_attributes */
  describe("defs/lithology_attributes", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/lithology_attributes")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an att_type", function(done) {
      request(host)
        .get("/api/defs/lithology_attributes?att_type=bedform")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a lith_att", function(done) {
      request(host)
        .get("/api/defs/lithology_attributes?lith_att=mounds")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a lith att id", function(done) {
      request(host)
        .get("/api/defs/lithology_attributes?id=1")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all records", function(done) {
      request(host)
        .get("/api/defs/lithology_attributes?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/defs/lithology_attributes?lith_att=mounds&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* defs/columns */
  describe("defs/columns", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/columns")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a col_group_id", function(done) {
      request(host)
        .get("/api/defs/columns?col_group_id=17")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a col_id", function(done) {
      request(host)
        .get("/api/defs/columns?col_id=17")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a col_name", function(done) {
      request(host)
        .get("/api/defs/columns?col_name=Eastern%20Kentucky")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all columns", function(done) {
      request(host)
        .get("/api/defs/columns?id=1")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
  });

/* defs/econs */
  describe("defs/econs", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/econs")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an econ_class", function(done) {
      request(host)
        .get("/api/defs/econs?econ_class=energy")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an econ_type", function(done) {
      request(host)
        .get("/api/defs/econs?econ_type=hydrocarbon")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an econ", function(done) {
      request(host)
        .get("/api/defs/econs?environ=oil%20shale")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an econ_id", function(done) {
      request(host)
        .get("/api/defs/econs?id=1")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all econ definitions", function(done) {
      request(host)
        .get("/api/defs/econs?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .expect(function(res) {
          if (res.body.success.data.length < 15) {
            throw new Error("Not enough results returned on defs/econs");
          }
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return CSV", function(done) {
      request(host)
        .get("/api/defs/econs?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });


/* defs/environments */
  describe("defs/environments", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/environments")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an environment class", function(done) {
      request(host)
        .get("/api/defs/environments?environ_class=non-marine")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an environment type", function(done) {
      request(host)
        .get("/api/defs/environments?environ_type=carbonate")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an environment", function(done) {
      request(host)
        .get("/api/defs/environments?environ=open%20shallow%20subtidal")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an environment id", function(done) {
      request(host)
        .get("/api/defs/environments?id=1")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all environment definitions", function(done) {
      request(host)
        .get("/api/defs/environments?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return CSV", function(done) {
      request(host)
        .get("/api/defs/environments?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* defs/intervals */
  describe("defs/intervals", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/intervals")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a timescale parameter", function(done) {
      request(host)
        .get("/api/defs/intervals?timescale=new%20zealand%20ages")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an interval id", function(done) {
      request(host)
        .get("/api/defs/intervals?id=366")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all definitions", function(done) {
      request(host)
        .get("/api/defs/intervals?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return CSV", function(done) {
      request(host)
        .get("/api/defs/intervals?timescale=new%20zealand%20ages&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an early and late age", function(done) {
      request(host)
        .get("/api/defs/intervals?late_age=0&early_age=130")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age", function(done) {
      request(host)
        .get("/api/defs/intervals?age=200")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

  });

  describe("defs/timescales", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/timescales")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all timescales", function(done) {
      request(host)
        .get("/api/defs/timescales?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/defs/timescales?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("defs/projects", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/projects")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all projects", function(done) {
      request(host)
        .get("/api/defs/projects?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/defs/projects?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  
  describe("defs/groups", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/groups")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all column groups", function(done) {
      request(host)
        .get("/api/defs/groups?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/defs/groups?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });


/* defs/strat_names */
  describe("defs/strat_names", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/defs/strat_names")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a strat id", function(done) {
      request(host)
        .get("/api/defs/strat_names?id=1")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a strat name", function(done) {
      request(host)
        .get("/api/defs/strat_names?name=Abercrombie")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a strat rank", function(done) {
      request(host)
        .get("/api/defs/strat_names?rank=Gp")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return all strat names", function(done) {
      request(host)
        .get("/api/defs/strat_names?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/defs/strat_names?name=Abercrombie&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* section_stats */
  describe("section_stats", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/section_stats")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    /*it("should accept an age model", function(done) {
      request(host)
        .get("/api/section_stats?age_model=continuous")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });*/

    it("should return all section stats", function(done) {
      request(host)
        .get("/api/section_stats?all")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output CSV", function(done) {
      request(host)
        .get("/api/section_stats?all&format=csv")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .expect("Content-Type", "text/csv; charset=utf-8")
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* paleogeography */
  describe("paleogeography", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/paleogeography")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age parameter", function(done) {
      request(host)
        .get("/api/paleogeography?age=271")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an interval name", function(done) {
      request(host)
        .get("/api/paleogeography?interval_name=Permian")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return topojson", function(done) {
      request(host)
        .get("/api/paleogeography?interval_name=Permian&format=topojson")
        .expect(aSuccessfulRequest)
        .expect(topoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* geologic_units */
  describe("geologic_units", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/geologic_units")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a latitude and longitude", function(done) {
      this.timeout(3000);
      
      request(host)
        .get("/api/geologic_units?lat=43&lng=-89.3&type=gmna")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a time interval name on GMUS", function(done) {
      this.timeout(5000);

      request(host)
        .get("/api/geologic_units?interval_name=Pliocene&type=gmus")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a time interval name on GMNA", function(done) {
      request(host)
        .get("/api/geologic_units?interval_name=Permian&type=gmna")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a unit name on GMUS", function(done) {
      this.timeout(4000);

      request(host)
        .get("/api/geologic_units?unit_name=Mancos%20Shale&type=gmus")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return geometry when asked", function(done) {
      request(host)
        .get("/api/geologic_units?lat=43&lng=-89.3&type=gmna&format=geojson")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* geologic_units/intersection */
  describe("geologic_units/intersection", function() {
    it("should return metadata", function(done) {
      request(host)
        .get("/api/geologic_units/intersection")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a WKT LineString", function(done) {
      request(host)
        .get("/api/geologic_units/intersection?LINESTRING(-91.8896484375 43.26120612479979,-83.1005859375 43.068887774169625)")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

  });
/* geologic_units/map */
  describe("geologic_units/map", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/geologic_units/map")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should throw an error if a required parameter is ommitted", function(done) {
      request(host)
        .get("/api/geologic_units/map?interval_name=Permian")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a type and interval name", function(done) {
      request(host)
        .get("/api/geologic_units/map?interval_name=Permian&type=gmna")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should output Topojson", function(done) {
      request(host)
        .get("/api/geologic_units/map?interval_name=Permian&type=gmna&format=topojson")
        .expect(aSuccessfulRequest)
        .expect(topoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* mobile/point */
  describe("mobile/point", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/mobile/point")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a latitude and longitude", function(done) {
      request(host)
        .get("/api/mobile/point?lat=43&lng=-89")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

  });

/* mobile/point_details */
  describe("mobile/point_details", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/mobile/point_details")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a lat and lng", function(done) {
      request(host)
        .get("/api/mobile/point_details?lat=43&lng=-89")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .expect(function(res) {
          if (!res.body.success.data[0].column || !res.body.success.data[0].gmus) {
            throw new Error("Response missing a data type");
          }
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a col_id and unit_id", function(done) {
      request(host)
        .get("/api/mobile/point_details?col_id=187&unit_id=184506")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .expect(function(res) {
          if (!res.body.success.data[0].column || !res.body.success.data[0].gmus) {
            throw new Error("Response missing a data type");
          }
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

/* fossil_collections */
  describe("mobile/fossil_collections", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/mobile/fossil_collections")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a unit_id", function(done) {
      request(host)
        .get("/api/mobile/fossil_collections?unit_id=154")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
        .expect(function(res) {
          if (res.body.success.data.length < 2) {
            throw new Error("PBDB collections not returned");
          }
          if (res.body.success.data[0].id !== 111035) {
            throw new Error("Wrong collections returned on moble/fossil_collections")
          }
          if (res.body.success.data[1].name !== "Lookout Mountain") {
            throw new Error("Wrong collections returned on moble/fossil_collections")
          }
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    })
  });
  
  describe("Mancos test cases", function() {
    it("should return point data for Detroit", function(done) {
      request(host)
        .get("/api/v1/mobile/point?lat=42.331427&lng=-83.045754")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(function(res) {
          if (res.body.success.data.uid !== 60404) {
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
      request(host)
        .get("/api/v1/mobile/point_details?lat=42.331427&lng=-83.045754")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/v1/mobile/point?lat=43.651893&lng=-79.381713")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(function(res) {
          if (res.body.success.data.uid !== 33901) {
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
      request(host)
        .get("/api/v1/mobile/point_details?lat=43.651893&lng=-79.381713")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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
      request(host)
        .get("/api/v1/mobile/point?lat=-34.565383&lng=-58.452759")
        .expect(aSuccessfulRequest)
        .expect(json)
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
      request(host)
        .get("/api/v1/mobile/point_details?lat=-34.565383&lng=-58.452759")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(atLeastOneResult)
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

  });
});