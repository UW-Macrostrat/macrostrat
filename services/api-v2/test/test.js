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
  if (!res.body.success) {
    throw new Error("Request was not successful, but should have been");
  }
}

function csv(res) {
  if (res.statusCode !== 200) {
    throw new Error("Bad status code");
  }
  if (res.headers["access-control-allow-origin"] !== "*") {
    throw new Error("Wrong access-control-allow-origin headers");
  }
  if (res.body.length < 10) {
    throw new Error("No CSV output recieved");
  }
}

describe('Routes', function() {
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
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age", function(done) {
      request(host)
        .get("/api/columns?age=271")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept an age_top and age_bottom", function(done) {
      request(host)
        .get("/api/columns?age_top=200&age_bottom=250")
        .expect(aSuccessfulRequest)
        .expect(geoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should return geojson and topojson", function(done) {
      request(host)
        .get("/api/columns?age=2&format=topojson")
        .expect(aSuccessfulRequest)
        .expect(topoJSON)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("unit", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/unit")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a unit id", function(done) {
      request(host)
        .get("/api/unit?id=527")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a parameter 'pbdb'", function(done) {
      request(host)
        .get("/api/unit?id=527&pbdb=true")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(function(res) {
          if (!res.body.success.data[0].pbdb_collections) {
            throw new Error("PBDB collections missing when requested");
          }
        })
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should accept a response parameter", function(done) {
      request(host)
        .get("/api/unit?id=527&response=long")
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
    })
  });

  describe("units", function() {
    this.timeout(20000);

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
  });

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
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    })
  });

  describe("lith_definitions", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/lith_definitions")
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
        .get("/api/lith_definitions?id=3")
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
        .get("/api/lith_definitions?lith_class=sedimentary")
        .expect(aSuccessfulRequest)
        .expect(json)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });

    it("should show all lith definitions when asked", function(done) {
      request(host)
        .get("/api/lith_definitions?all")
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
        .get("/api/lith_definitions?id=3")
        .expect(aSuccessfulRequest)
        .expect(csv)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("lithatt_definitions", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/lithatt_definitions")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("environ_definitions", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/environ_definitions")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("interval_definitions", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/interval_definitions")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("strat_names", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/strat_names")
        .expect(aSuccessfulRequest)
        .expect(json)
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

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
  });

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
  });

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
  });

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
  });

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
  });

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
  });

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
  });
});