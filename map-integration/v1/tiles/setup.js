(function() {
  var async = require("async");
  var pg = require("pg");
  var carto = require("carto");
  var fs = require("fs-extra");
  var path = require('path')

  var yaml = require('yamljs')
  var credentials = yaml.load(path.join(__dirname, '..', 'credentials.yml'))

  var config = require("./config");

  // Factory for querying Postgres
  function queryPg(db, sql, params, callback) {
    pg.connect("postgres://" + credentials.pg_user + "@" + credentials.pg_host + ":" + credentials.pg_port + "/" + db, function(err, client, done) {
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
      "name": "",
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
    "attribution": "Data providers, UW-Macrostrat, John J Czaplewski <john@czaplewski.org>"
  }

  // Gets the extend and centroid of a given scale, and returns an mml layer configuration
  function createLayer(scale, callback) {
    // Copy the template
    var layer = JSON.parse(JSON.stringify(layerTemplate));
    layer["Datasource"]["table"] = `(SELECT x.map_id, x.scale, s.color, x.geom FROM carto_new.${scale} x JOIN lookup_${scale} s ON s.map_id = x.map_id JOIN maps.sources ON x.source_id = sources.source_id ORDER BY sources.priority ASC) subset`
    layer["id"] = `burwell_${scale}`
    layer["class"] = "burwell"
    layer["name"] = `burwell_${scale}`
    layer["minZoom"] = Math.min.apply(Math, config.scaleMap[scale])
    layer["maxZoom"] = Math.max.apply(Math, config.scaleMap[scale])
    callback(layer)
  }

  // Gets the extend and centroid of a given scale, and returns an mml layer configuration
  function createLayerLines(scale, callback) {
    // Copy the template
    var layer = JSON.parse(JSON.stringify(layerTemplateLines));
    let sql = `
      SELECT x.line_id, x.geom, q.direction, q.type
      FROM carto_new.lines_${scale} x
      LEFT JOIN (
          ${config.layerOrder[scale].map(s => {
            return `SELECT * FROM lines.${s}`
          }).join(' UNION ALL ')}
      ) q on q.line_id = x.line_id
    `
    layer["Datasource"]["table"] = `(${sql}) subset`
    layer["id"] = `burwell_lines_${scale}`
    layer["class"] = "lines"
    layer["name"] = `burwell_lines_${scale}`
    layer["minZoom"] = Math.min.apply(Math, config.scaleMap[scale])
    layer["maxZoom"] = Math.max.apply(Math, config.scaleMap[scale])
    callback(layer)
  }

  // Build our styles from the database
  function buildStyles(layer, callback) {
    //console.log("--- Building styles ---");

    // First, rebuild the styles in the event any colors were changed
    queryPg("burwell", "SELECT DISTINCT interval_color AS color FROM macrostrat.intervals WHERE interval_color IS NOT NULL AND interval_color != ''", [], function(error, data) {
      var colors = data.rows;

      // Load the base styles
      var cartoCSS = fs.readFileSync(__dirname + '/styles/' + layer + '.css', 'utf8');

      // Compile the stylesheet
      for (var i = 0; i < colors.length; i++) {
        cartoCSS += `
          .burwell[color="${colors[i].color}"] {
            polygon-fill: ${colors[i].color};
          }
        `;
      }

      //fs.writeFileSync('./styles.mss', cartoCSS)

      // Append the styles to the project template object
      burwell["Stylesheet"].push({
        class: "burwell",
        data: cartoCSS
      });

      callback(null);
    });
  }

  // Create a new mmml project, convert it to Mapnik XML, and save it to the current directory
  function createProject(scale, layer, callback) {
    // Copy the project template
    var project = JSON.parse(JSON.stringify(burwell));

    project["minzoom"] = Math.min.apply(Math, config.scaleMap[scale]);
    project["maxzoom"] = Math.max.apply(Math, config.scaleMap[scale]);

    // Create a new layer for each scale that is a part of this scale's project as defined in layerOrder
    var layers = []
    async.each(config.layerOrder[scale], function(d, callback) {
      async.parallel([
        function(c) {
          if (config.mapLayers[layer].hasUnits) {
            createLayer(d, function(l) {
              //layers.push(l)
              c(null, l)
            })
          } else {
            c(null, null)
          }
        },
        function(c) {
          // Only add lines if A) this layer needs lines and B) we are iterating on the current scale
          if (config.mapLayers[layer].hasLines && d === scale) {
            createLayerLines(d, function(l) {
              c(null, l)
            })
          } else {
            c(null, null)
          }
        }
      ], function(error, result) {
        layers = layers.concat(result.filter(function(d) { if (d) return d }))
        callback(null)
      })
    }, function(error) {
      // Record the layers
      project["Layer"] = layers;
      fs.writeFileSync(`${__dirname}/test.mml`, JSON.stringify(project), 'utf8')
      // Convert the resultant mml file to Mapnik XML
      var mapnikXML = new carto.Renderer({
        //paths: [ __dirname ],
        filename: 'test.mml',
        local_data_dir: path.dirname('test.mml')
      }).render(project);

      // Save it
      fs.outputFile(`${__dirname}/compiled_styles/burwell_${scale}_${layer}.xml`, mapnikXML, function(error) {
        if (error) {
          console.log("Error wrting XML file for ", scale);
        }
        callback(null);
      });
    });
  }

  module.exports = function(layer, callback) {
    async.waterfall([
      // First build the styles
      function(callback) {
        buildStyles(layer, callback);
      },

      // For each scale, create and save and new project
      function(callback) {
        async.each(config.scales, function(scale, callback) {
          createProject(scale, layer, callback);
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
