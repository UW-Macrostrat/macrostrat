const fs = require('fs')
const path = require('path')
const carto = require("carto")
var cartoCSS = fs.readFileSync(`${__dirname}/styles.css`, 'utf8');

 var burwell = {
    "bounds": [-89,-179,89,179],
    "center": [0, 0, 1],
    "format": "png8",
    "interactivity": false,
    "minzoom": 0,
    "maxzoom": 16,
    "srs": "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over",
    "Stylesheet": [{ class: "burwell", data: cartoCSS }],
    "Layer": [{
      "geometry": "polygon",
      "Datasource": {
          "type": "postgis",
          "table": "",
          "key_field": "map_id",
          "geometry_field": "geom",
          "extent_cache": "auto",
          "extent": "-179,-89,179,89",
          "host": "localhost",
          "dbname": "burwell",
          "srid": "4326"
      },
      "id": "units",
      "class": "units",
      "srs-name": "WGS84",
      "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
      "advanced": {},
      "name": "units",
      "minZoom": "",
      "maxZoom": ""
  }, {
    "geometry": "linestring",
    "Datasource": {
        "type": "postgis",
        "table": "",
        "key_field": "map_id",
        "geometry_field": "geom",
        "extent_cache": "auto",
        "extent": "-179,-89,179,89",
        "host": "localhost",
        "dbname": "burwell",
        "srid": "4326"
    },
    "id": "lines",
    "class": "lines",
    "srs-name": "WGS84",
    "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
    "advanced": {},
    "name": "lines",
    "minZoom": "",
    "maxZoom": ""
}],
    "scale": 1,
    "metatile": 2,
    "name": "burwell",
    "description": "burwell",
    "attribution": "Data providers, UW-Macrostrat, John J Czaplewski <john@czaplewski.org>"
  }


fs.writeFileSync(`${__dirname}/test.mml`, JSON.stringify(burwell), 'utf8')
// Convert the resultant mml file to Mapnik XML
let mapnikXML = new carto.Renderer({
  //paths: [ __dirname ],
  filename: 'test.mml',
  local_data_dir: path.dirname('test.mml')
}).render(burwell);

// Save it
fs.writeFile(`${__dirname}/styles.xml`, mapnikXML, function(error) {
  if (error) {
    console.log("Error wrting XML file for ", scale);
  }

});
