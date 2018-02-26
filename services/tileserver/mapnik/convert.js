const fs = require('fs')
const path = require('path')
const carto = require('carto')
const async = require('async')
const pgHelper = require('@macrostrat/pg-helper')
const credentials = require('../credentials')
const config = require('../config')

let pg = new pgHelper({
  host: credentials.pg_host,
  user: credentials.pg_user,
  port: credentials.pg_port,
  database: 'burwell'
})

function makeLayer(scale, cartoCSS, callback) {
  let lineSQLJoin = config.layerOrder[scale].map(s => {
    return `SELECT * FROM lines.${s}`
  }).join(' UNION ALL ')

  let burwell = {
    "bounds": [-89,-179,89,179],
    "center": [0, 0, 1],
    "format": "png8",
    "interactivity": false,
    "minzoom": 0,
    "maxzoom": 16,
    "srs": "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over",
    "Stylesheet": [{ class: "units", data: cartoCSS }],
    "Layer": [{
      "geometry": "polygon",
      "Datasource": {
          "type": "postgis",
          "table": `(SELECT z.map_id, COALESCE(l.color, '#777777') AS color, z.geom FROM carto_new.${scale} z LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id) subset`,
          "key_field": "map_id",
          "geometry_field": "geom",
          "extent_cache": "auto",
          "extent": "-179,-89,179,89",
          "host": credentials.pg_host,
          "port": credentials.pg_port,
          "user": credentials.pg_user,
          "dbname": "burwell",
          "srid": "4326"
      },
      "id": `units_${scale}`,
      "class": "units",
      "srs-name": "WGS84",
      "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
      "advanced": {},
      "name": `units_${scale}`,
      "minZoom": "0",
      "maxZoom": "16"
  }, {
    "geometry": "linestring",
    "Datasource": {
        "type": "postgis",
        "table": `(SELECT x.line_id, x.geom, q.direction, q.type FROM carto_new.lines_${scale} x LEFT JOIN ( ${lineSQLJoin} ) q on q.line_id = x.line_id ) subset`,
        "key_field": "line_id",
        "geometry_field": "geom",
        "extent_cache": "auto",
        "extent": "-179,-89,179,89",
        "host": credentials.pg_host,
        "port": credentials.pg_port,
        "user": credentials.pg_user,
        "dbname": "burwell",
        "srid": "4326"
    },
    "id": "lines",
    "class": `lines_${scale}`,
    "srs-name": "WGS84",
    "srs": "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
    "advanced": {},
    "name": `lines_${scale}`,
    "minZoom": "0",
    "maxZoom": "16"
  }],
    "scale": 1,
    "metatile": 2,
    "name": "burwell",
    "description": "burwell",
    "attribution": "Data providers, UW-Macrostrat, John J Czaplewski <john@czaplewski.org>"
  }

  fs.writeFileSync(`${__dirname}/temp.mml`, JSON.stringify(burwell), 'utf8')
  // Convert the resultant mml file to Mapnik XML
  let mapnikXML = new carto.Renderer({
    //paths: [ __dirname ],
    filename: 'test.mml',
    local_data_dir: path.dirname('test.mml')
  }).render(burwell)

  // Save it
  fs.writeFile(`${__dirname}/burwell_${scale}_emphasized.xml`, mapnikXML, (error) => {
    if (error) {
      console.log("Error wrting XML file for ", scale)
    }
    callback()
  })
}

// Build our styles from the database
function buildStyles(callback) {
  // First, rebuild the styles in the event any colors were changed
  pg.query(`
    SELECT DISTINCT color
    FROM maps.legend
    WHERE color IS NOT NULL AND color != ''
  `, [], (error, data) => {
    let colors = data.map(c => {
      return `
        .units[color="${c.color}"] {
          polygon-fill: ${c.color};
        }
      `
    }).join(`
    `)

    // Load the base styles
    let cartoCSS = fs.readFileSync(`${__dirname}/styles.css`, 'utf8')

    callback(null, colors + cartoCSS)
  })
}




async.waterfall([
  (cb) => {
    buildStyles((error, cartoCSS) => {
      cb(null, cartoCSS)
    })
  },
  (cartoCSS, cb) => {
    async.eachLimit(config.scales, 1, (scale, done) => {
      makeLayer(scale, cartoCSS, (error) => {
        done()
      })
    })
  }
])
