/** Helper functions for data selection */

/** Convert a lithology into an array structure that shows the entire hierarchy. Useful for filtering by all hierarchy levels,
  and dumping the hierarchy into a text column of exported datasets.
*/
CREATE OR REPLACE FUNCTION macrostrat.lithology_hierarchy(lith macrostrat.liths) RETURNS text[] AS $$
DECLARE
  result text[];
BEGIN
  result := ARRAY[lith.lith_class::text];
  IF lith.lith_type IS NOT NULL AND lith.lith_type::text != all(result) THEN
    result := result || lith.lith_type::text;
  END IF;
  IF lith.lith_group IS NOT NULL AND lith.lith_group::text != all(result) THEN
    result := result || lith.lith_group::text;
  END IF;
  IF lith.lith IS NOT NULL AND lith.lith::text != all(result) THEN
    result := result || lith.lith::text;
  END IF;
  RETURN result;
END;
$$ LANGUAGE plpgsql;
