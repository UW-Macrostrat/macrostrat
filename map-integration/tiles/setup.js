var async = require("async");
var pg = require("pg");
var carto = require("carto");
var fs = require("fs");
var path = require("path");
var extend = require("util")._extend;
var credentials = require("./credentials");
var config = require("./config");

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

// This is the template for each layer
var layerTemplate = {
    "geometry": "polygon",
    "Datasource": {
        "type": "postgis",
        "table": "",
        "key_field": "map_id",
        "geometry_field": "geom",
        "extent_cache": "auto",
        "extent": "-179,-89,179,89",
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

// Gets the extend and centroid of a given scale, and returns an mml layer configuration
function createLayer(scale, callback) {
  // Copy the template
  var layer = JSON.parse(JSON.stringify(layerTemplate));

  // Fill in the attributes
  layer["Datasource"]["table"] = "(SELECT x.map_id, x.group_id, x.color, geom FROM lookup_" + scale + " x JOIN maps." + scale + " s ON s.map_id = x.map_id) subset";
  layer["id"] = "burwell_" + scale;
  layer["name"] = "burwell_" + scale;
  layer["minZoom"] = Math.min.apply(Math, config.scaleMap[scale]);
  layer["maxZoom"] = Math.max.apply(Math, config.scaleMap[scale]);
  callback(layer);
}

// Build our styles from the database
function buildStyles(callback) {
  console.log("--- Building styles ---");

  // First, rebuild the styles in the event any colors were changed
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

    // Append the styles to the project template object
    burwell["Stylesheet"].push({
      class: "burwell",
      data: cartoCSS
    });

    callback(null);
  });
}

// Create a new mmml project, convert it to Mapnik XML, and save it to the current directory
function createProject(scale, callback) {
  // Copy the project template
  var project = JSON.parse(JSON.stringify(burwell));

  project["minzoom"] = Math.min.apply(Math, config.scaleMap[scale]);
  project["maxzoom"] = Math.max.apply(Math, config.scaleMap[scale]);

  // Create a new layer for each scale that is a part of this scale's project as defined in layerOrder
  async.map(config.layerOrder[scale], function(d, callback) {
    createLayer(d, function(layer) {
      callback(null, layer);
    });
  }, function(error, layers) {
    // Record the layers
    project["Layer"] = layers;

    // Convert the resultant mml file to Mapnik XML
    var mapnikXML = new carto.Renderer({
      paths: [ __dirname ],
      local_data_dir: __dirname
    }).render(project);

    // Save it
    fs.writeFile(__dirname + "/burwell_" + scale + ".xml", mapnikXML, function(error) {
      if (error) {
        console.log("Error wrting mml file for ", scale);
      }
      console.log("--- Created config for ", scale, " ---");
      callback(null);
    });
  });

}

// Things start here
async.waterfall([
  // First build the styles
  buildStyles,

  // For each scale, create and save and new project
  function(callback) {
    async.each(config.scales, createProject, function(error) {
      callback(null);
    });
  }

  // Be done
], function(error, results) {
  if (error) {
    console.log(error);
  }
  process.exit(0);
});
