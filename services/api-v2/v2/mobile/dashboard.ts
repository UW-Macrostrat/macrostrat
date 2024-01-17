const api = require("../api");
const larkin = require("../larkin");
const async = require("async");

const above = {
  large: "medium",
  medium: "small",
  small: "tiny",
};

function queryCarto(scale, lng, lat, callback) {
  scale = scale || "large";

  larkin.queryPg(
    "burwell",
    `
    SELECT
      x.map_id,
      x.source_id,
      l.name,
      l.best_age_bottom::numeric AS b_age,
      l.best_age_top::numeric AS t_age,
      (
          SELECT COALESCE(array_to_json(array_agg(row_to_json(best_liths))), '[]') AS liths
          FROM (
              SELECT lith AS name, a.prop, lith_color AS color, lith_fill AS fill
              FROM (
                  SELECT DISTINCT ON (combined.id) combined.id AS lith_id, prop
                  FROM (
                      SELECT id, 0 AS prop
                      FROM macrostrat.liths
                      WHERE id = ANY((SELECT unnest(l.lith_ids)))
                      UNION ALL
                      SELECT lith_id, sum(prop)/count(*) AS prop
                      FROM (
                          SELECT lith_id,
                            CASE
                              WHEN prop ~ '^[0-9\.]+$'
                                THEN prop::numeric
                              ELSE
                                0
                            END as prop
                          FROM macrostrat.unit_liths
                          WHERE unit_id = ANY((SELECT unnest(l.unit_ids)))
                      ) ul
                      GROUP BY lith_id
                      ORDER BY prop DESC
                  ) combined
              ) a
              JOIN macrostrat.liths ON liths.id = lith_id
              order by prop DESC
          ) best_liths
      ) AS lith,
      (
          SELECT COALESCE(array_to_json(array_agg(DISTINCT rank_name)), '[]') AS strat_name
          FROM macrostrat.lookup_strat_names WHERE strat_name_id = ANY((SELECT unnest(strat_name_ids)))
      ) AS strat_names,
      COALESCE((
          SELECT interval_name
          FROM macrostrat.intervals
          JOIN macrostrat.timescales_intervals ti ON ti.interval_id = intervals.id
          WHERE age_top <= l.best_age_top AND age_bottom >= l.best_age_bottom
          AND interval_type = 'period' and timescale_id = 20
          ORDER BY age_bottom - age_top
      ), (
        SELECT
          CASE
            WHEN l.b_interval IS NULL
          THEN ''
          WHEN l.b_interval=l.t_interval
          THEN (SELECT interval_name
            FROM macrostrat.intervals ib
            WHERE id = l.t_interval)
          ELSE
            (SELECT concat((SELECT interval_name
            FROM macrostrat.intervals ia
            WHERE id = l.b_interval), ' - ', (SELECT interval_name
            FROM macrostrat.intervals ib
            WHERE id = l.t_interval)))
          END
      )) AS c_int_name,
      COALESCE((
          SELECT interval_color
          FROM macrostrat.intervals
          JOIN macrostrat.timescales_intervals ti ON ti.interval_id = intervals.id
          WHERE age_top <= l.best_age_top AND age_bottom >= l.best_age_bottom
          AND interval_type = 'period' and timescale_id = 20
          ORDER BY age_bottom - age_top
      ), l.color) AS int_color
    FROM carto_new.${scale} x
    JOIN maps.map_legend ml ON ml.map_id = x.map_id
    JOIN maps.legend l ON ml.legend_id = l.legend_id
    WHERE ST_Intersects(x.geom, $1)
  `,
    [`SRID=4326;POINT(${lng} ${lat})`],
    (error, result) => {
      if (error) {
        console.log("error here", scale, lng, lat);
        return callback(error);
      }
      if (!result || !result.rows || !result.rows.length) {
        // try going a scale up
        if (above[scale]) {
          queryCarto(above[scale], lng, lat, callback);
        } else {
          callback(null, null);
        }
      } else {
        callback(null, result.rows[0]);
      }
    },
  );
}

module.exports = (req, res, next) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  if (!req.query.lng || !req.query.lat) {
    return larkin.error(req, res, next);
  }
  req.query.lng = larkin.normalizeLng(req.query.lng);

  async.parallel(
    {
      rocks: (callback) => {
        queryCarto(null, req.query.lng, req.query.lat, (error, data) => {
          callback(null, data);
        });
      },

      elevation: (callback) => {
        require("../elevation")(req, null, null, function (error, result) {
          let elevation = result && result.length ? result[0].elevation : null;
          callback(null, elevation);
        });
      },

      regions: (callback) => {
        larkin.queryPg(
          "burwell",
          `
        SELECT sub.boundary_id, sub.name, sub.boundary_group, sub.boundary_type, sub.boundary_class, sub.descrip, sub.wiki_link,
        row_to_json(
          (SELECT x FROM (SELECT sources.source_id, sources.name, sources.url, sources.ref_title, sources.authors, sources.ref_year, sources.ref_source, COALESCE(sources.isbn_doi, '') AS isbn_doi) x)
       ) AS ref
        FROM
            (
            SELECT
                boundary_id,
                source_id,
                COALESCE(name, '') AS name,
                COALESCE(boundary_group, '') AS boundary_group,
                COALESCE(boundary_type, '') AS boundary_type,
                COALESCE(initcap(boundary_class), '') AS boundary_class,
                COALESCE(descrip, '') AS descrip,
                COALESCE(wiki_link, '') AS wiki_link,
                row_number() OVER(PARTITION BY boundary_class ORDER BY ST_Area(geom) ASC) as rn
            FROM geologic_boundaries.boundaries
            WHERE ST_Intersects(geom, $1)
            ) sub
        JOIN geologic_boundaries.sources ON sub.source_id = sources.source_id
        WHERE rn = 1
      `,
          [`SRID=4326;POINT(${req.query.lng} ${req.query.lat})`],
          (error, result) => {
            let regions =
              result && result.rows && result.rows.length ? result.rows : [];
            callback(null, regions);
          },
        );
      },
    },
    (error, data) => {
      if (error) {
        return larkin.error(req, res, next);
      }
      let summary = data.rocks || {};
      summary["elevation"] = data.elevation;
      summary["regions"] = data.regions;

      if (summary["b_age"]) {
        summary["b_age"] = parseFloat(summary["b_age"]);
      }
      if (summary["t_age"]) {
        summary["t_age"] = parseFloat(summary["t_age"]);
      }
      if (summary.lith && summary.lith.length) {
        summary["lith_color"] = summary.lith[0].color;
      }
      larkin.sendData(
        req,
        res,
        next,
        {
          format: api.acceptedFormats.standard[req.query.format]
            ? req.query.format
            : "json",
          bare: api.acceptedFormats.bare[req.query.format] ? true : false,
          compact: true,
        },
        {
          data: summary,
        },
      );
    },
  );
};
