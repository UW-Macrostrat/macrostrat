var config = require('../tiles/config');
var credentials = require('../tiles/credentials');
var pg = require('pg');

if (!process.argv[2] || config.scales.indexOf(process.argv[2]) < 0) {
  console.log('Please provide a valid burwell scale. Example: `node build_flat.js small`');
  process.exit(1)
}

function queryPg(sql, params, callback) {
  pg.connect('postgres://' + credentials.pg.user + '@' + credentials.pg.host + '/burwell', function(err, client, done) {
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


var scale = process.argv[2]

console.time('query')
queryPg(`
  DROP TABLE IF EXISTS carto.flat_${scale};

  CREATE TABLE carto.flat_${scale} AS

  -- Get the reference geom of all sources flagged as the given scale and with high priority
  WITH ${scale}_priority_ref AS (
    SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
    FROM maps.sources
    WHERE scale = '${scale}'
    AND priority IS TRUE
  ),

  -- Get the actual geometries that belong to the above scale and priority
  ${scale}_priorities AS (
    SELECT s.map_id, ST_SetSRID(s.geom, 4326) geom
    FROM maps.${scale} s
    JOIN maps.sources ON s.source_id = sources.source_id
    WHERE priority IS TRUE
  ),

  -- Get all polygons of the target scale that DON'T intersect the reference geometry of high priority sources
  -- These don't need to be cut!
  ${scale}_nonpriority_unique AS (
    SELECT s.map_id, ST_SetSRID(s.geom, 4326) geom
    FROM maps.${scale} s
    JOIN maps.sources ON s.source_id = sources.source_id
    LEFT JOIN ${scale}_priority_ref pr
    ON ST_Intersects(ST_SetSRID(s.geom, 4326), st_setsrid(pr.geom, 4326))
    WHERE pr.id IS NULL
    AND priority IS FALSE
    AND ST_Geometrytype(s.geom) != 'ST_LineString'
  ),

  -- Get all polygons of the target scale that intersect the reference geometry of the high priority sources
  -- Cut them by the high priority sources
  ${scale}_nonpriority_clipped AS (
    SELECT s.map_id, ST_Difference(ST_SetSRID(s.geom, 4326), pr.geom) geom
    FROM maps.${scale} s
    JOIN ${scale}_priority_ref pr
    ON ST_Intersects(ST_SetSRID(s.geom, 4326), pr.geom)
    JOIN maps.sources ON s.source_id = sources.source_id
    WHERE priority IS FALSE
  ),

  -- Join together:
  --    + All geometries that are high priority (never cut)
  --    + Low priority geometries that don't intersect the high priority ones
  --    + Low priority geometries that DO intersect the high priority ones

  SELECT map_id, geom
  FROM ${scale}_priorities
  WHERE ST_NumGeometries(geom) > 0
  UNION
  SELECT map_id, geom
  FROM ${scale}_nonpriority_unique
  WHERE ST_NumGeometries(geom) > 0
  UNION
  SELECT map_id, geom
  FROM ${scale}_nonpriority_clipped
  WHERE ST_NumGeometries(geom) > 0
`, [], function(error, result) {
  if (error) {
    console.log('Something went wrong ', error)
    process.exit(1)
  } else {
    console.log('Created table carto.flat_' + process.argv[2])
    console.timeEnd('query')
    process.exit(2)
  }
})
