(function() {
  var async = require("async")
  var carto = require("carto")
  var fs = require("fs-extra")
  var path = require('path')
  var config = require("./config")
  var yaml = require('yamljs')
  var credentials = yaml.load(path.join(__dirname, '..', 'credentials.yml'))

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
          "port": credentials.pg_port,
          "user": credentials.pg_user,
          "password": credentials.pg_password,
          "dbname": "burwell",
          "srid": "4326"
      },
      "id": "",
      "class": "burwell",
      "srs-name": "WGS84",
      "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
      "advanced": {},
      "name": "units",
      "minZoom": "",
      "maxZoom": ""
  }

  // This is the template for each layer
  var layerTemplateLines = {
      "geometry": "linestring",
      "Datasource": {
          "type": "postgis",
          "table": "",
          "key_field": "line_id",
          "geometry_field": "geom",
          "extent_cache": "auto",
          "extent": "-179,-89,179,89",
          "host": "localhost",
          "port": credentials.pg_port,
          "user": credentials.pg_user,
          "password": credentials.pg_password,
          "dbname": "burwell",
          "srid": "4326"
      },
      "id": "",
      "class": "lines",
      "srs-name": "WGS84",
      "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
      "advanced": {},
      "name": "lines",
      "minZoom": "",
      "maxZoom": ""
  }

  // Instantiate the project template that will hold each layer
  var burwell = {
    "bounds": [-89,-179,89,179],
    "center": [0, 0, 1],
    "interactivity": false,
    "minzoom": 0,
    "maxzoom": 13,
    "srs": "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over",
    "Stylesheet": [],
    "Layer": [],
    "scale": 1,
    "metatile": 1,
    "name": "burwell",
    "description": "burwell",
    "attribution": "Data providers, UW-Macrostrat, John J Czaplewski <john@czaplewski.org>"
  }

  // Gets the extend and centroid of a given scale, and returns an mml layer configuration
  function createLayer(scale, callback) {
    // Copy the template
    var layer = JSON.parse(JSON.stringify(layerTemplate));
    layer["Datasource"]["table"] = `(SELECT map_id, name, age, lith, descrip, comments, t_int, b_int, color, geom FROM carto.${scale} ) subset`
    layer["id"] = "burwell_units"
    layer["class"] = "burwell_units"
    layer["minZoom"] = 0
    layer["maxZoom"] = 16
    callback(layer)
  }

  // Gets the extend and centroid of a given scale, and returns an mml layer configuration
  function createLayerLines(scale, callback) {
    // Copy the template
    var layer = JSON.parse(JSON.stringify(layerTemplateLines));
    layer["Datasource"]["table"] = `(SELECT x.line_id, x.geom, x.direction, x.type FROM carto.lines_${scale} x) subset`
    layer["id"] = 'burwell_lines'
    layer["class"] = "burwell_lines"
    layer["minZoom"] = 0
    layer["maxZoom"] = 16
    callback(layer)
  }

  // Create a new mmml project, convert it to Mapnik XML, and save it to the current directory
  function createProject(scale, layer, callback) {
    // Copy the project template
    var project = JSON.parse(JSON.stringify(burwell));

    project["minzoom"] = Math.min.apply(Math, config.scaleMap[scale]);
    project["maxzoom"] = Math.max.apply(Math, config.scaleMap[scale]);

    // Create a new layer for each scale that is a part of this scale's project as defined in layerOrder
    var layers = []

    async.parallel([
      function(c) {
        createLayer(scale, function(l) {
          //layers.push(l)
          c(null, l)
        })
      },
      function(c) {
        createLayerLines(scale, function(l) {
        //  layers.push(l)
          c(null, l)
        })
      }
    ], function(error, result) {
      // Record the layers
      project["Layer"] = layers.concat(result.filter(function(d) { if (d) return d }))

      // Convert the resultant mml file to Mapnik XML
      var mapnikXML = new carto.Renderer({
        paths: [ __dirname ],
        local_data_dir: __dirname
      }).render(project)

      // Save it
      fs.outputFile(`${__dirname}/compiled_styles/burwell_vector_${scale}.xml`, mapnikXML, function(error) {
        if (error) {
          console.log("Error wrting XML file for ", scale)
        }
        callback(null)
      })
    })
  }

  module.exports = function(layer, callback) {
    async.waterfall([
      // For each scale, create and save and new project
      function(callback) {
        async.each(config.scales, function(scale, callback) {
          createProject(scale, null, callback);
        }, function(error) {
          callback(null);
        });
      }

      // Be done
    ], function(error, results) {
      if (error) {
        callback(error);
      } else {
        callback(null);
      }
    });
  }

}());
