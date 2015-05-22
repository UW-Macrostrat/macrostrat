module.exports = function() {
  
  describe("root", require("./root"));
  describe("columns", require("./columns"));
  describe("sections", require("./sections"));
  describe("units", require("./units"));
  describe("fossils", require("./fossils"));
  describe("stats", require("./stats"));
  describe("section_stats", require("./section_stats"));

  describe("defs", require("./defs"));
  describe("defs/lithologies", require("./defs_lithologies"));
  describe("defs/lithology_attributes", require("./defs_lithology_attributes"));
  describe("defs/columns", require("./defs_columns"));
  describe("defs/econs", require("./defs_econs"));
  describe("defs/environments", require("./defs_environments"));
  describe("defs/intervals", require("./defs_intervals"));
  describe("defs/timescales", require("./defs_timescales"));
  describe("defs/projects", require("./defs_projects"));
  describe("defs/groups", require("./defs_groups"));
  describe("defs/strat_names", require("./defs_strat_names"));

  describe("paleogeography", require("./paleogeography"));
  describe("geologic_units/gmna", require("./geologic_units_gmna"));
  describe("geologic_units/gmus", require("./geologic_units_gmus"));
  describe("geologic_units/intersection", require("./geologic_units_intersection"));

  describe("mobile/point", require("./mobile_point"));
  describe("mobile/point_details", require("./mobile_point_details"));
  describe("mobile/fossil_collections", require("./mobile_fossil_collections"));
  describe("Mancos test cases", require("./mancos_test_cases"));

}
