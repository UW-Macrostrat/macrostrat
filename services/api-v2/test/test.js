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
  if (!res.body.success) {
    throw new Error("Request was unsuccessful");
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

describe('Routes', function() {
  describe('root', function() {
    it('should return a list of all visible routes', function(done) {
      request(host)
        .get("/api")
        .expect(aSuccessfulRequest)
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
        .expect(metadata)
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
        .expect(metadata)
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
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("units", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/units")
        .expect(aSuccessfulRequest)
        .expect(metadata)
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
        .expect(metadata)
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
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });

  describe("lith_definitions", function() {
    it('should return metadata', function(done) {
      request(host)
        .get("/api/lith_definitions")
        .expect(aSuccessfulRequest)
        .expect(metadata)
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
        .expect(metadata)
        .end(function(error, res) {
          if (error) return done(error);
          done();
        });
    });
  });
});