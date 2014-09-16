var http = require("http"),
    async = require("async"),
    clc = require('cli-color');

var host = "http://localhost:5000",
    warn = clc.red.bold;

function getJSON(url, callback) {
  http.get(url, function(res) {
    var body = "";

    res.on("data", function(chunk) {
        body += chunk;
    });

    res.on("end", function() {
      if (JSON.parse(body).success && res.statusCode === 200) {
        callback(null, "passed");
      } else {
        callback(JSON.parse(body), null);
      }
    });
  }).on("error", function(error) {
    callback(error, null);
  });
};

/*
1. go to /api
2. get all routes
3. hit each route, grabbing the first example
4. hit the example route, getting all fields

*/
async.parallel({
  root: function(callback) {
    getJSON(host + "/api", function(error, result) {
      if (error) {
        callback({"path": "root", "error": error});
      } else {
        console.log("/api : " + clc.green("passed"));
        callback(null, result);
      }
    });
  },

  column: function(callback) {
    var tests = ["/column", "/column?id=17", "/column?lat=50&lng=-80", "/column?id=49&response=short"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "column", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/column : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  columns: function(callback) {
    var tests = ["/columns", "/columns?interval_name=Permian", "/columns?age=271", "/columns?age_top=200&age_bottom=250", "/columns?age_top=200&age_bottom=250&format=topojson"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "columns", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/columns : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  unit: function(callback) {
    var tests = ["/unit", "/unit?id=527", "/unit?id=527&pbdb=true", "/unit?id=527&pbdb=true&response=long"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "unit", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/unit : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  units: function(callback) {
    var tests = ["/units", "/units?interval_name=Permian", "/units?age=271", "/units?age_top=200&age_bottom=250"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "units", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/units : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  fossils: function(callback) {
    var tests = ["/fossils", "/fossils?interval_name=Permian", "/fossils?age=271", "/fossils?age_top=200&age_bottom=250", "/fossils?age_top=200&age_bottom=250&output=topojson"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "fossils", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/fossils : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  stats: function(callback) {
    var tests = ["/stats", "/stats?all"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "stats", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/stats : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  lith_definitions: function(callback) {
    var tests = ["/lith_definitions", "/lith_definitions?all"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "lith_definitions", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/lith_definitions : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  lithatt_definitions: function(callback) {
    var tests = ["/lithatt_definitions", "/lithatt_definitions?all"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "lithatt_definitions", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/lithatt_definitions : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  environ_definitions: function(callback) {
    var tests = ["/environ_definitions", "/environ_definitions?all"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "environ_definitions", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/environ_definitions : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  interval_definitions: function(callback) {
    var tests = ["/interval_definitions", "/interval_definitions?all"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "interval_definitions", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/interval_definitions : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  strat_names: function(callback) {
    var tests = ["/strat_names", "/strat_names?all"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "strat_names", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/strat_names : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  section_stats: function(callback) {
    var tests = ["/section_stats", "/section_stats?all", "/section_stats?age_model=continuous"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "section_stats", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/section_stats : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  },

  paleogeography: function(callback) {
    var tests = ["/paleogeography", "/paleogeography?interval_name=Permian", "/paleogeography?age=500", "/paleogeography?interval_name=Early Jurassic&output=topojson"];

    async.each(tests, function(test, callbackB) {
      getJSON(host + "/api" + test, function(error, result) {
        if (error) {
          callbackB({"path": "paleogeography", "error": error});
        } else {
          callbackB();
        }
      });
    }, function(error) {
      if (error) {
        callback(error);
      } else {
        console.log("/api/paleogeography : " + clc.green("passed"));
        callback(null, "passed");
      }
    });
  }

}, function(error, results) {
  if (error) {
    console.log(warn("Error on " + error.path), JSON.stringify(error));
    process.exit();
  } else {
    process.exit();
  }
});