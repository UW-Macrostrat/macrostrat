var async = require("async");
var pg = require("pg");
var carto = require("carto");
var fs = require("fs");
var path = require("path");
var extend = require("util")._extend;
var credentials = require("./credentials");

// Factory for querying Postgres
function queryPg(db, sql, params, callback) {
  pg.connect("postgres://" + credentials.pg.user + "@" + credentials.pg.host + "/" + db, function(err, client, done) {
    if (err) {
      callback(err);
    } else {
      var query = client.query(sql, params, function(err, result) {
        done();
        if (err) {
          callback(err);
        } else {
          callback(null, result);
        }
      });
    }
  });
}

// All of our burwell scales
var scales = ["tiny", "small", "medium", "large"];

// Which zoom levels correspond to which map scales
var scaleMap = {
  "tiny": ["0", "1", "2", "3"],
  "small": ["4", "5"],
  "medium": ["6", "7", "8", "9", "10"],
  "large": ["11", "12", "13"]
}

var layerOrder = {
  "tiny": ["tiny"],
  "small": ["tiny", "large", "medium", "small"],
  "medium": ["large", "small", "medium"],
  "large": ["medium", "large"]
}

// This is the template for each layer
var layerTemplate = {
    "geometry": "polygon",
    "extent": [],
    "Datasource": {
        "type": "postgis",
        "table": "",
        "key_field": "map_id",
        "geometry_field": "geom",
        "extent_cache": "auto",
        "extent": "",
        "host": "localhost",
        "port": "5432",
        "user": "john",
        "dbname": "burwell",
        "srid": "4326"
    },
    "id": "",
    "class": "burwell",
    "srs-name": "WGS84",
    "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
    "advanced": {},
    "name": "",
    "minZoom": "",
    "maxZoom": ""
}

// Instantiate the project template that will hold each layer
var burwell = {
  "bounds": [-89,-179,89,179],
  "center": [0, 0, 1],
  "format": "png8",
  "interactivity": false,
  "minzoom": 0,
  "maxzoom": 13,
  "srs": "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over",
  "Stylesheet": [],
  "Layer": [],
  "scale": 1,
  "metatile": 2,
  "name": "burwell",
  "description": "burwell",
  "attribution": "Data providers, UW-Macrostrat, John J Czaplewski <jczaplew@gmail.com>"
}

function createLayer(scale, callback) {
  // Find the extend and the centroid
  queryPg("burwell", "SELECT ST_Extent(s.geom) AS extent, ST_AsText(ST_Centroid(ST_Extent(geom))) AS centroid FROM lookup_" + scale + " x JOIN maps." + scale + " s ON s.map_id = x.map_id", [], function(error, data) {
    var attrs = data.rows[0];

    var layer = extend({}, layerTemplate);

    var extent = attrs["extent"].replace(" ", ",").replace("BOX(", "").replace(")", "");
    var center = attrs["centroid"].replace("POINT(", "").replace(")", "");

    layer["bounds"] = extent.split(",").map(function(d) { return parseFloat(d) });
    layer["center"] = center.split(" ").map(function(d) { return parseFloat(d) }).push(3);
    layer["extent"] = [-179, -89, 179, 89];
    layer["Datasource"]["extent"] = "-179,-89,179,89";
    layer["Datasource"]["table"] = "(SELECT x.map_id, x.group_id, x.color, geom FROM lookup_" + scale + " x JOIN maps." + scale + " s ON s.map_id = x.map_id) subset";
    layer["id"] = "burwell_" + scale;
    layer["name"] = "burwell_" + scale;
    layer["minZoom"] = Math.min.apply(Math, scaleMap[scale]);
    layer["maxZoom"] = Math.max.apply(Math, scaleMap[scale]);

    callback(layer);
  });
}

function buildStyles(callback) {
  console.log("--- Building styles ---");

  // First, rebuild the file `styles.mss` in the event any colors were changed
  queryPg("burwell", "SELECT DISTINCT interval_color AS color FROM macrostrat.intervals WHERE interval_color IS NOT NULL AND interval_color != ''", [], function(error, data) {
    var colors = data.rows;

    var cartoCSS = `
      .burwell {
        polygon-opacity:1;
        polygon-fill: #000;
        line-color: #aaa;
        line-width: 0.0;
      }
      .burwell[color="null"] {
         polygon-fill: #777777;
      }
      .burwell[color=null] {
         polygon-fill: #777777;
      }
      .burwell[color=""] {
         polygon-fill: #777777;
      }
    `;

    // Compile the stylesheet
    for (var i = 0; i < colors.length; i++) {
      cartoCSS += `
        .burwell[color="${colors[i].color}"] {
          polygon-fill: ${colors[i].color};
        }
      `;
    }

    burwell["Stylesheet"].push({
      id: 1,
      class: "burwell",
      data: cartoCSS
    });

    callback(null);
  });
}

function createProject(scale, callback) {
  var project = extend({}, burwell);
  project["minzoom"] = Math.min.apply(Math, scaleMap[scale]);
  project["maxzoom"] = Math.max.apply(Math, scaleMap[scale]);

  async.map(layerOrder[scale], function(d, callback) {
    createLayer(d, function(layer) {
      callback(null, layer);
    });
  }, function(error, layers) {
    project["Layer"] = layers;

    var mapnikXML = new carto.Renderer({
      paths: [ __dirname ],
      local_data_dir: __dirname
    }).render(project);

    fs.writeFile(__dirname + "/burwell_" + scale + ".xml", mapnikXML, function(error) {
      if (error) {
        console.log("Error wrting mml file for ", scale);
      }
      console.log("--- Created config for ", scale, " ---");
      callback(null);
    });
  });

}

async.waterfall([
  buildStyles,

  function(callback) {
    async.each(scales, createProject, function(error) {
      callback(null);
    });
  }

], function(error, results) {
  if (error) {
    console.log(error);
  }
  process.exit(0);
});
