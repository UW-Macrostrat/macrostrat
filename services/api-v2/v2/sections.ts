import { getUnitsData } from "./units";

var api = require("./api"),
  _ = require("underscore"),
  larkin = require("./larkin");

function newSection(data) {
  return {
    t_age: data.t_age,
    b_age: data.b_age,
    units: [data],
  };
}

module.exports = async function (req, res, next) {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }

  try {
    // First pass the request to units and get the units back

    const units = await getUnitsData(req);

    // The sauce. Process the units into sections, grouped by column
    const columns = processUnitsIntoSections(units);

    // Summarize each section and flatten into sections
    const sections = summarizeSections(columns, req);

    // Format sections for CSV if needed
    if (req.query.response === "long" && req.query.format === "csv") {
      for (let i = 0; i < sections.length; i++) {
        sections[i].lith = larkin.pipifyAttrs(sections[i].lith);
        sections[i].environ = larkin.pipifyAttrs(sections[i].environ);
        sections[i].econ = larkin.pipifyAttrs(sections[i].econ);
      }
    }

    larkin.sendData(
      req,
      res,
      next,
      {
        format: api.acceptedFormats.standard[req.query.format]
          ? req.query.format
          : "json",
      },
      {
        data: sections,
      },
    );
  } catch (error) {
    return larkin.error(req, res, next, error);
  }
};

function processUnitsIntoSections(units) {
  // First group by column
  const columns = _.groupBy(units, function (d) {
    return d.col_id;
  });

  // Reorganize a bit
  Object.keys(columns).forEach(function (d) {
    columns[d] = {
      sections: (function () {
        // This holds the resultant packages
        const sections = [];

        // Our first section is the first unit, as they are sorted by ascending t_age
        let currentSection = newSection(columns[d][0]);

        for (let i = 1; i < columns[d].length; i++) {
          if (
            columns[d][i].t_age >= currentSection.t_age &&
            columns[d][i].t_age <= currentSection.b_age
          ) {
            // Bump the b_age down if needed
            if (columns[d][i].b_age > currentSection.b_age) {
              currentSection.b_age = columns[d][i].b_age;
            }
            currentSection.units.push(columns[d][i]);
          } else {
            sections.push(currentSection);
            currentSection = newSection(columns[d][i]);
          }
        }
        // Add the last current section
        sections.push(currentSection);

        return sections;
      })(),
    };
  });

  return columns;
}

function summarizeSections(columns, req) {
  const sections = [];

  Object.keys(columns).forEach(function (col_id) {
    for (let i = 0; i < columns[col_id].sections.length; i++) {
      // Summarize the section and push it to our result queue
      const section = {
        col_id: parseInt(col_id),
        col_area: parseFloat(columns[col_id].sections[i].units[0].col_area),
        section_id: columns[col_id].sections[i].units[0].section_id,
        project_id: columns[col_id].sections[i].units[0].project_id,

        max_thick: columns[col_id].sections[i].units
          .map(function (d) {
            return d.max_thick;
          })
          .reduce(function (a, b) {
            return a + b;
          }, 0)
          .toFixed(2),
        min_thick: columns[col_id].sections[i].units
          .map(function (d) {
            return d.min_thick;
          })
          .reduce(function (a, b) {
            return a + b;
          }, 0)
          .toFixed(2),

        t_age: _.min(columns[col_id].sections[i].units, function (d) {
          return d.t_age;
        }).t_age,
        b_age: _.max(columns[col_id].sections[i].units, function (d) {
          return d.b_age;
        }).b_age,

        pbdb_collections: columns[col_id].sections[i].units
          .map(function (d) {
            return d.pbdb_collections;
          })
          .reduce(function (a, b) {
            return a + b;
          }, 0),
      };

      if (req.query.response === "long") {
        section["lith"] = larkin.summarizeAttribute(
          columns[col_id].sections[i].units,
          "lith",
        );
        section["environ"] = larkin.summarizeAttribute(
          columns[col_id].sections[i].units,
          "environ",
        );
        section["econ"] = larkin.summarizeAttribute(
          columns[col_id].sections[i].units,
          "econ",
        );
      }

      sections.push(section);
    }
  });

  return sections;
}
