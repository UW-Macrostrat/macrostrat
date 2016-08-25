var config = require('../tiles/config');
var credentials = require('../tiles/credentials');
var pg = require('pg');

if (!process.argv[2] || config.scales.indexOf(process.argv[2]) < 0) {
  console.log('Please provide a valid burwell scale. Example: `node build_carto.js small`');
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

/*

Each scale involved in the building of a `carto` table (see tiles/config.layerOrder) needs to be processed into a flat layer.
You can think of it as getting all sources of a given scale, and then laying 'priority' sources on top to create a smooth,
homogenous layer.

*/
function prepScale(scale) {
  return `
  -- Get the reference geom of all sources flagged as the given scale and with high priority
  ${scale}_priority_ref AS (
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
  ${scale} AS (
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
  )`;
}

var sql = `
DROP TABLE IF EXISTS carto.${process.argv[2]};
CREATE TABLE carto.${process.argv[2]} AS WITH `;

var scalePrepSQL = [];

// These are the scales that go into the composite of the carto table for the target scale
var scales = config.layerOrder[process.argv[2]];

scales.forEach(function(scale) {
  scalePrepSQL.push(prepScale(scale));
});

// Unique bottom and clipped bottom
scales.forEach(function(scale, idx) {
  if (idx === scales.length - 1) {
    return;
  }
  var scalesAbove = scales.map(function(d, i) {
    if (i > idx) return "'" + d + "'";
  }).filter(function(d) {
    if (d) return d;
  }).join(',');

  scalePrepSQL.push(`
  -- Get polygons from the scale that don't intersect the target scale at all
  unique_${scale} AS (
    SELECT t.map_id, t.geom
    FROM ${scale} t
    LEFT JOIN (
      SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
      FROM maps.sources
      WHERE scale IN (${scalesAbove})
    ) sr
    ON ST_Intersects(t.geom, sr.geom)
    WHERE sr.id IS NULL
    AND ST_Geometrytype(t.geom) != 'ST_LineString'
  ),
  -- Clip the parts of the scale that intersect all scales 'above' in priority
  ${scale}_clipped AS (
    SELECT t.map_id, ST_Difference(t.geom, sr.geom) geom
    FROM ${scale} t
    JOIN (
      SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
      FROM maps.sources
      WHERE scale IN (${scalesAbove})
    ) sr
    ON ST_Intersects(t.geom, sr.geom)
  )`);
});

var resultQuery = 'result AS ( '

// Union everything
scales.forEach(function(scale, idx) {
  if (idx != scales.length - 1) {
    resultQuery += `
    SELECT map_id, '${scale}' AS scale, geom
    FROM unique_${scale}
    UNION
    SELECT map_id, '${scale}' AS scale, geom
    FROM ${scale}_clipped
    UNION`
  } else {
    resultQuery += `
    SELECT map_id, '${scale}' AS scale, geom
    FROM ${scale}
    `
  }
});

resultQuery += ')';
scalePrepSQL.push(resultQuery);
sql += scalePrepSQL.join(',');

var mJoin = scales.map(function(scale) {
  return `SELECT map_id, source_id, name, strat_name, age, lith, descrip, comments, t_interval, b_interval FROM maps.${scale}`;
}).join(' UNION ');
var lJoin = scales.map(function(scale) {
  return `SELECT map_id, best_age_top, best_age_bottom, color FROM public.lookup_${scale}`
}).join(' UNION ');

sql += `
SELECT r.map_id, r.scale, m.source_id,
COALESCE(m.name, '') AS name,
COALESCE(m.strat_name, '') AS strat_name,
COALESCE(m.age, '') AS age,
COALESCE(m.lith, '') AS lith,
COALESCE(m.descrip, '') AS descrip,
COALESCE(m.comments, '') AS comments,
cast(l.best_age_top as numeric) AS best_age_top,
cast(l.best_age_bottom as numeric) AS best_age_bottom, it.interval_name t_int, ib.interval_name b_int, l.color,
ST_SetSRID(r.geom, 4326) AS geom
FROM result r
LEFT JOIN (
  ${mJoin}
) m ON r.map_id = m.map_id
LEFT JOIN (
  ${lJoin}
) l ON r.map_id = l.map_id
JOIN macrostrat.intervals it ON m.t_interval = it.id
JOIN macrostrat.intervals ib ON m.b_interval = ib.id
WHERE ST_NumGeometries(r.geom) > 0;

CREATE INDEX ON carto.${process.argv[2]} (map_id);
CREATE INDEX ON carto.${process.argv[2]} USING GiST (geom);
`;

console.time('query');
queryPg(sql, [], function(error) {
  if (error) {
    console.log(sql);
    console.log('Something went wrong ', error);
    process.exit(1);
  } else {
    console.log('Created table carto.' + process.argv[2])
    console.timeEnd('query');
    process.exit(2);
  }
});
