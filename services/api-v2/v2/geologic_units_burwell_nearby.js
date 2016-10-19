var api = require("./api"),
    async = require("async"),
    larkin = require("./larkin");

// To whom it may concern: sorry this is so hairy. Magic ain't cheap.
var sql = {
  lithologies: `
  WITH nn AS (
    SELECT lith_id, lith, lith_type, lith_class, lith_color, distance
    FROM (
      (SELECT lith_id, liths.lith, lith_type, lith_class, lith_color, geom, ST_Distance(geom, st_setsrid(st_makepoint($1, $2),4326)) AS distance
       FROM maps.medium m
       LEFT JOIN maps.map_liths ON m.map_id = map_liths.map_id
       LEFT JOIN macrostrat.liths ON liths.id = map_liths.lith_id
       WHERE liths.lith IS NOT NULL
       ORDER BY geom <#> st_setsrid(st_makepoint($1,$2),4326)
       LIMIT 1000)
      UNION ALL
      (SELECT lith_id, liths.lith, lith_type, lith_class, lith_color, geom, ST_Distance(geom, st_setsrid(st_makepoint($1, $2),4326)) AS distance
       FROM maps.small m
       LEFT JOIN maps.map_liths ON m.map_id = map_liths.map_id
       LEFT JOIN macrostrat.liths ON liths.id = map_liths.lith_id
       WHERE liths.lith IS NOT NULL
       ORDER BY geom <#> st_setsrid(st_makepoint($1,$2),4326)
       LIMIT 1000)
      UNION ALL
      (SELECT lith_id, liths.lith, lith_type, lith_class, lith_color, geom, ST_Distance(geom, st_setsrid(st_makepoint($1, $2),4326)) AS distance
       FROM maps.large m
       LEFT JOIN maps.map_liths ON m.map_id = map_liths.map_id
       LEFT JOIN macrostrat.liths ON liths.id = map_liths.lith_id
       WHERE liths.lith IS NOT NULL
       ORDER BY geom <#> st_setsrid(st_makepoint($1,$2),4326)
       LIMIT 1000)
    ) a
    ORDER BY distance
    LIMIT 1000
  ),

  nnlimit AS (
    SELECT DISTINCT ON (lith_id) lith_id, lith, lith_type, lith_class, lith_color, distance
    FROM nn
    ORDER BY lith_id, distance
  )

  SELECT lith_id, lith AS name, lith_type AS type, lith_class AS class, lith_color AS color
  FROM nnlimit
  ORDER BY distance
  LIMIT 5;`,

  strat_names: `
  WITH nn AS (
    SELECT strat_name_id, strat_name, strat_name_long, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period, geom, row_number() OVER() as row_number
    FROM (
      SELECT strat_name_id, strat_name, strat_name_long, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period, geom FROM (
        SELECT msn.strat_name_id, lookup_strat_names.strat_name, lookup_strat_names.rank_name AS strat_name_long, bed_name AS bed, mbr_name AS mbr, fm_name AS fm, gp_name AS gp, sgp_name AS sgp, early_age AS b_age, late_age AS t_age, b_period, t_period, geom
         FROM maps.large m
         LEFT JOIN maps.map_strat_names msn ON m.map_id = msn.map_id
         LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id = msn.strat_name_id
         WHERE msn.strat_name_id IS NOT NULL
         ORDER BY geom <#> st_setsrid(st_makepoint($1, $2),4326)
         LIMIT 100
      ) a
      UNION ALL
      SELECT strat_name_id, strat_name, strat_name_long, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period, geom FROM (
        SELECT msn.strat_name_id, lookup_strat_names.strat_name, lookup_strat_names.rank_name AS strat_name_long, bed_name AS bed, mbr_name AS mbr, fm_name AS fm, gp_name AS gp, sgp_name AS sgp, early_age AS b_age, late_age AS t_age, b_period, t_period, geom
         FROM maps.medium m
         LEFT JOIN maps.map_strat_names msn ON m.map_id = msn.map_id
         LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id = msn.strat_name_id
         WHERE msn.strat_name_id IS NOT NULL
         ORDER BY geom <#> st_setsrid(st_makepoint($1, $2),4326)
         LIMIT 100
      ) b
      UNION ALL
      SELECT strat_name_id, strat_name, strat_name_long, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period, geom FROM (
        SELECT msn.strat_name_id, lookup_strat_names.strat_name, lookup_strat_names.rank_name as strat_name_long, bed_name AS bed, mbr_name AS mbr, fm_name AS fm, gp_name AS gp, sgp_name AS sgp, early_age AS b_age, late_age AS t_age, b_period, t_period, geom
         FROM maps.small m
         LEFT JOIN maps.map_strat_names msn ON m.map_id = msn.map_id
         LEFT JOIN macrostrat.lookup_strat_names ON lookup_strat_names.strat_name_id = msn.strat_name_id
         WHERE msn.strat_name_id IS NOT NULL
         ORDER BY geom <#> st_setsrid(st_makepoint($1, $2),4326)
         LIMIT 100
      ) c
    )a
    ORDER BY geom <#> st_setsrid(st_makepoint($1, $2),4326)
    LIMIT 100
  ),

  nnlimit AS (
    SELECT DISTINCT ON (strat_name_id) strat_name_id, strat_name, strat_name_long, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period, row_number
    FROM nn
  )

  SELECT strat_name_id, strat_name, strat_name_long, bed, mbr, fm, gp, sgp, b_age, t_age, b_period, t_period
  FROM nnlimit
  ORDER BY row_number
  LIMIT 5;`,

  intervals: `
    WITH nn AS (
      SELECT interval_id, row_number() OVER() AS row_number
      FROM (
        SELECT map_id, t_interval as interval_id, geom from maps.large
        UNION ALL
        SELECT map_id, b_interval AS interval_id, geom from maps.large
        UNION ALL
        SELECT map_id, t_interval as interval_id, geom from maps.medium
        UNION ALL
        SELECT map_id, b_interval AS interval_id, geom from maps.medium
        UNION ALL
        SELECT map_id, t_interval as interval_id, geom from maps.small
        UNION ALL
        SELECT map_id, b_interval AS interval_id, geom from maps.small
      ) a
      ORDER BY geom <-> st_setsrid(st_makepoint($1,$2),4326)
      LIMIT 1000
    ),

    nnlimit AS (
      SELECT DISTINCT ON (interval_id) interval_id, row_number
      FROM nn
      ORDER BY interval_id, row_number
    )

    SELECT interval_id AS int_id, interval_name AS name, age_bottom AS b_age, age_top AS t_age, interval_color AS color
    FROM nnlimit
    JOIN macrostrat.intervals on nnlimit.interval_id = intervals.id
    ORDER BY row_number
    LIMIT 5;`,

  map_units: `
    WITH subset AS (
      SELECT map_id, name, 'tiny' AS scale, geom
      FROM maps.tiny
      WHERE ST_Intersects(geom, ST_Buffer($1::geography, 3200)::geometry)
      UNION ALL
      SELECT map_id, name, 'small' AS scale, geom
      FROM maps.small
      WHERE ST_Intersects(geom, ST_Buffer($1::geography, 3200)::geometry)
      UNION ALL
      SELECT map_id, name, 'medium' AS scale, geom
      FROM maps.medium
      WHERE ST_Intersects(geom, ST_Buffer($1::geography, 3200)::geometry)
      UNION ALL
      SELECT map_id, name, 'large' AS scale, geom
      FROM maps.large
      WHERE ST_Intersects(geom, ST_Buffer($1::geography, 3200)::geometry)
    ),
    best_scale AS (
      SELECT
        CASE WHEN 'large' IN (SELECT DISTINCT scale FROM subset)
          THEN ARRAY['large', 'medium']
        WHEN 'medium' IN (SELECT DISTINCT scale FROM subset)
          THEN ARRAY['medium', 'small']
        WHEN 'small' IN (SELECT DISTINCT scale FROM subset)
          THEN ARRAY['small', 'tiny']
        WHEN 'tiny' IN (SELECT DISTINCT scale FROM subset)
          THEN ARRAY['tiny']
        ELSE null
       END AS best
    ),
    units AS (
      SELECT first_value(map_id) OVER (
        PARTITION BY name
        ORDER BY ST_Distance(geom, $1)
      ) map_id, first_value(name) OVER (
        PARTITION BY name
        ORDER BY ST_Distance(geom, $1)
      ) unit_name, ST_Distance(geom::geography, $1::geography)::int distance
      FROM subset
      WHERE ST_Intersects(geom, ST_Buffer($1::geography, 3200)::geometry)
      AND name NOT ILIKE '%water%' AND (SELECT scale = ANY(best) FROM best_scale)
      GROUP BY map_id, name, geom
      ORDER BY distance
    )

    SELECT map_id, unit_name, min(distance) AS distance
    FROM units
    GROUP BY map_id, unit_name
    ORDER BY min(distance);
  `,

  places: `
    WITH first AS (
      SELECT notes, ST_Distance(ST_SetSRID(geom, 4326)::geography, $1::geography)::int d
      FROM checkins
      ORDER BY ST_SetSRID(geom, 4326) <-> $1
      LIMIT 15
    )
    SELECT notes AS place, d AS distance
    FROM first
    WHERE d < 80000;
  `
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

  async.parallel({
    strat_names: function(callback) {
      larkin.queryPg("burwell", sql.strat_names, [req.query.lng, req.query.lat], function(error, data) {
        if (error) {
          callback(error);
        } else {
          callback(null, data.rows);
        }
      });
    },

    lithologies: function(callback) {
      larkin.queryPg("burwell", sql.lithologies, [req.query.lng, req.query.lat], function(error, data) {
        if (error) {
          callback(error);
        } else {
          callback(null, data.rows);
        }
      });
    },

    intervals: function(callback) {
      larkin.queryPg("burwell", sql.intervals, [req.query.lng, req.query.lat], function(error, data) {
        if (error) {
          callback(error);
        } else {
          callback(null, data.rows);
        }
      });
    },

    map_units: function(callback) {
      larkin.queryPg("burwell", sql.map_units, ['SRID=4326;POINT(' + req.query.lng + ' ' + req.query.lat + ')'], function(error, data) {
        if (error) {
          callback(error);
        } else {
          callback(null, data.rows);
        }
      })
    },

    places: function(callback) {
      larkin.queryPg("rockd", sql.places, ['SRID=4326;POINT(' + req.query.lng + ' ' + req.query.lat + ')'], function(error, data) {
        if (error) {
          callback(error);
        } else {
          callback(null, data.rows);
        }
      })
    }
  }, function(error, results) {
    if (error) {
      larkin.error(req, res, next, error);
    } else {
      larkin.sendData(req, res, next, {
        format: (api.acceptedFormats.standard[req.query.format]) ? req.query.format : "json",
        bare: (api.acceptedFormats.bare[req.query.format]) ? true : false,
        compact: true
      }, {
        data: results
      });
    }
  });

}
