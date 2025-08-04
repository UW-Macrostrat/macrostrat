/** Create a view to mirror this table in the correct location
  * in order to keep the macrostrat schema clean and dedicated to stratigraphy.
  */
CREATE VIEW maps.ingest_process AS
SELECT * FROM maps_metadata.ingest_process;
