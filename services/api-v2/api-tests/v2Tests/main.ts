import type { Suite } from "mocha";
require("../settings");

const loadTests = (path: string) => {
  return (this: Suite) => {
    return require(path);
  };
};

describe("api/v2", () => {
  describe("root", loadTests("./root"));
  describe("columns", loadTests("./columns"));
  describe("sections", loadTests("./sections"));
  describe("units", loadTests("./units"));
  describe("fossils", loadTests("./fossils"));
  describe("stats", loadTests("./stats"));

  describe("defs", loadTests("./defs"));
  describe("defs/lithologies", loadTests("./defs_lithologies"));
  describe(
    "defs/lithology_attributes",
    loadTests("./defs_lithology_attributes"),
  );
  describe("defs/columns", loadTests("./defs_columns"));
  describe("defs/econs", loadTests("./defs_econs"));
  describe("defs/environments", loadTests("./defs_environments"));
  describe("defs/intervals", loadTests("./defs_intervals"));
  describe("defs/measurements", loadTests("./defs_measurements"));
  describe("defs/minerals", loadTests("./defs_minerals"));
  describe("defs/timescales", loadTests("./defs_timescales"));
  describe("defs/plates", loadTests("./defs_plates"));
  describe("defs/projects", loadTests("./defs_projects"));
  describe("defs/groups", loadTests("./defs_groups"));
  describe("defs/strat_names", loadTests("./defs_strat_names"));
  describe("defs/strat_name_concepts", loadTests("./defs_strat_name_concepts"));
  describe("defs/structures", loadTests("./defs_structures"));
  describe("defs/refs", loadTests("./defs_refs"));
  describe("defs/sources", loadTests("./defs_sources"));

  describe("paleogeography", loadTests("./paleogeography"));
  //describe("geologic_units/gmna", loadTests("./geologic_units_gmna"), null, true);
  //describe("geologic_units/gmus", loadTests("./geologic_units_gmus"));
  describe("geologic_units/burwell", loadTests("./geologic_units_burwell"));

  describe("carto/small", loadTests("./carto_small"));

  describe("tiles", loadTests("./tiles"));

  describe("mobile/point", loadTests("./mobile_point"));
  //describe("mobile/point_details", loadTests("./mobile_point_details"));
  describe(
    "mobile/fossil_collections",
    loadTests("./mobile_fossil_collections"),
  );
  describe("mobile/macro_summary", loadTests("./mobile_macro_summary"));
  describe("mobile/map_query", loadTests("./mobile_map_query"));
  //describe("Mancos test cases", loadTests("./mancos_test_cases"));
});
