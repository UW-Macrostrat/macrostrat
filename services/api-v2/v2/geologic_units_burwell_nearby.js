var api = require("./api"),
    async = require("async"),
    larkin = require("./larkin");

var parentOrder = {
  "bed": ["mbr", "fm", "gp", "sgp"],
  "mbr": ["fm", "gp", "sgp"],
  "fm": ["gp", "sgp"],
  "gp": ["sgp"],
  "sgp": []
}
var abbrevs = {
  "mbr": "Member",
  "fm": "Formation",
  "gp": "Group",
  "sgp": "Supergroup"
}
// To whom it may concern: sorry this is so hairy. Magic ain't cheap.
var sql = {
  lithologies: `
    WITH first AS (
      SELECT DISTINCT ON (lith_id) lith_id, distance
      FROM (
        SELECT lith_id, ST_Distance(geom, st_setsrid(st_makepoint($1, $2),4326)) AS distance
        FROM maps.:scale m
        JOIN maps.map_liths ON m.map_id = map_liths.map_id
        ORDER BY geom <-> st_setsrid(st_makepoint($1, $2),4326)
        LIMIT 100
      ) a
      ORDER BY lith_id, distance
    )
    SELECT lith_id, lith AS name, lith_type AS type, lith_class AS class, lith_color AS color
    FROM first
    JOIN macrostrat.liths ON liths.id = first.lith_id
    ORDER BY distance ASC
    LIMIT 10`,

  strat_names: `
    SELECT DISTINCT ON (strat_name_long) strat_name_id, strat_name, strat_name_long, rank, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period FROM (
      SELECT strat_name_id, strat_name, strat_name_long, rank, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period FROM (
        SELECT DISTINCT ON (strat_name_id) strat_name_id, strat_name, strat_name_long, rank, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period, geom, distance FROM (
          SELECT
            msn.strat_name_id,
            lookup_strat_names.strat_name,
            lookup_strat_names.rank_name AS strat_name_long,
            lookup_strat_names.rank,
            bed_name AS bed,
            mbr_name AS mbr,
            fm_name AS fm,
            gp_name AS gp,
            sgp_name AS sgp,
            early_age AS b_age,
            late_age AS t_age,
            b_period, t_period,
            geom,
            ST_Distance(geom, st_setsrid(st_makepoint($1, $2),4326)) AS distance
           FROM maps.:scale m
           JOIN maps.map_strat_names msn ON m.map_id = msn.map_id
           JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id = msn.strat_name_id
           ORDER BY geom <-> st_setsrid(st_makepoint($1, $2),4326)
           LIMIT 100
        ) a
        ORDER BY strat_name_id, distance
      ) b
      WHERE strat_name_id IN (
        SELECT strat_name_id
        FROM macrostrat.strat_name_footprints
        WHERE ST_Intersects(geom, st_setsrid(st_makepoint($1, $2),4326))
      )
      ORDER BY distance
    ) c
    LIMIT 10;
  `,

  intervals: `
  WITH first AS (
    SELECT DISTINCT ON (interval_id) interval_id, distance
    FROM (
      SELECT
        map_id,
        t_interval as interval_id,
        geom,
        ST_Distance(geom, st_setsrid(st_makepoint($1, $2),4326)) AS distance
      FROM maps.:scale
      ORDER BY geom <-> st_setsrid(st_makepoint($1, $2),4326)
      LIMIT 1000
     ) a
     ORDER BY interval_id, distance
  )
  SELECT interval_id AS int_id, interval_name AS name, age_bottom AS b_age, age_top AS t_age, interval_color AS color
  FROM first
  JOIN macrostrat.intervals on first.interval_id = intervals.id
  ORDER BY distance ASC
  LIMIT 5;`,

  map_units: `
  SELECT map_id, name AS unit_name, distance, int_name
  FROM (
      SELECT DISTINCT ON (name) map_id, name, int_name, distance
      FROM (
          SELECT
            mm.map_id,
            COALESCE(name, CONCAT('Undifferentiated ', age)) AS name,
            ST_Distance(geom::geography, st_setsrid(st_makepoint($1, $2), 4326)::geography)::int AS distance,
              (SELECT COALESCE(interval_name, '')
              FROM macrostrat.intervals
              JOIN macrostrat.timescales_intervals ON intervals.id = timescales_intervals.interval_id
              JOIN macrostrat.timescales ON timescales_intervals.timescale_id = timescales.id
              WHERE age_top <= mm.best_age_top AND age_bottom >= mm.best_age_bottom
              AND timescales.id IN (11,14)
              ORDER BY age_bottom - age_top
              LIMIT 1
          ) AS int_name
          FROM maps.:scale m
          JOIN lookup_:scale mm on m.map_id = mm.map_id
          ORDER BY geom <-> st_setsrid(st_makepoint($1, $2),4326)
          LIMIT 200
      ) a
      ORDER BY name, distance
  ) b
  ORDER BY distance
  LIMIT 10;
  `,

  // places: `
  //   WITH first AS (
  //     SELECT notes, ST_Distance(ST_SetSRID(geom, 4326)::geography, $1::geography)::int d
  //     FROM checkins
  //     ORDER BY ST_SetSRID(geom, 4326) <-> $1
  //     LIMIT 15
  //   )
  //   SELECT notes AS place, d AS distance
  //   FROM first
  //   WHERE d < 80000;
  // `
}


module.exports = function(req, res, next) {
  if (Object.keys(req.query).length < 1) {
    larkin.info(req, res, next);
    return;
  }

  if (!req.query.lat || !req.query.lng) {
    larkin.error(req, res, next);
    return;
  }

  req.query.lng = larkin.normalizeLng(parseFloat(req.query.lng).toFixed(4))
  req.query.lat = parseFloat(req.query.lat).toFixed(4)

  async.waterfall([
    function(cb) {
      larkin.queryPg("burwell", `
      SELECT
        CASE
          WHEN (
            SELECT
              CASE
                WHEN count(*) > 0 THEN True
                ELSE False
               END
            FROM maps.large
            WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint($1, $2),4326))
          ) THEN 'large'
          WHEN (
            SELECT
              CASE
                WHEN count(*) > 0 THEN True
                ELSE False
               END
            FROM maps.medium
            WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint($1, $2),4326))
          ) THEN 'medium'
          WHEN (
            SELECT
              CASE
                WHEN count(*) > 0 THEN True
                ELSE False
               END
            FROM maps.small
            WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint($1, $2),4326))
          ) THEN 'small'
          ELSE ''
        END AS scale
      `, [ req.query.lng, req.query.lat ], function(error, result) {
        if (error || !result.rows) return cb(error)
        cb(null, result.rows[0].scale)
      })
    }, function(scale, cb) {
      if (scale === '') {
        return cb(null, [])
      }
      async.parallel({
        strat_names: function(callback) {
          larkin.queryPg("burwell", sql.strat_names.replace(':scale', scale), [req.query.lng, req.query.lat], function(error, data) {
            if (error) {
              callback(error);
            } else {
              var names = data.rows.map( d => {
                var rank = d.rank.toLowerCase()
                if (rank === 'subgp') {
                  return null
                }
                var parent = ''
                for (var i = 0; i < parentOrder[rank].length; i++) {
                  if (d[parentOrder[rank][i]]) {
                    parent = d[parentOrder[rank][i]] + " " + abbrevs[parentOrder[rank][i]]
                    continue
                  }
                }

                return {
                  strat_name_long: d.strat_name_long,
                  strat_name_id: d.strat_name_id,
                  strat_name: d.strat_name,
                  b_age: d.b_age,
                  b_period: d.b_period,
                  t_age: d.t_age,
                  t_period: d.t_period,
                  parent: parent
                }
              })


              callback(null, names)
            }
          });
        },

        lithologies: function(callback) {
          larkin.queryPg("burwell", sql.lithologies.replace(':scale', scale), [req.query.lng, req.query.lat], function(error, data) {
            if (error) {
              callback(error);
            } else {
              callback(null, data.rows);
            }
          });
        },

        intervals: function(callback) {
          larkin.queryPg("burwell", sql.intervals.replace(':scale', scale), [req.query.lng, req.query.lat], function(error, data) {
            if (error) {
              callback(error);
            } else {
              callback(null, data.rows);
            }
          });
        },

        map_units: function(callback) {
          larkin.queryPg("burwell", sql.map_units.replace(/:scale/g, scale), [req.query.lng, req.query.lat], function(error, data) {
            if (error) {
              callback(error);
            } else {
              callback(null, data.rows);
            }
          })
        },
        //
        // places: function(callback) {
        //   larkin.queryPg("rockd", sql.places, ['SRID=4326;POINT(' + req.query.lng + ' ' + req.query.lat + ')'], function(error, data) {
        //     if (error) {
        //       callback(error);
        //     } else {
        //       callback(null, data.rows);
        //     }
        //   })
        // }
      }, function(error, results) {
        if (error) {
          cb(error)
        } else {
          cb(null, results)
        }
      })
    }
  ], function(error, results) {
    if (error) {
      return larkin.error(req, res, next, error, 500)
    }
    larkin.sendData(req, res, next, {
      format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
      bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
      compact: true
    }, {
      data: results
    });
  })
}
