/** Recursive function to get all descendant project IDs **/
CREATE OR REPLACE FUNCTION macrostrat.flattened_project_ids(project_ids integer[]) RETURNS integer[] AS $$
DECLARE
  result_ids integer[] := ARRAY[]::integer[];
  current_ids integer[] := project_ids;
  child_ids integer[];
BEGIN
  LOOP
    EXIT WHEN array_length(current_ids, 1) IS NULL;
    result_ids := result_ids || current_ids;
    SELECT array_agg(pt.child_id)
    INTO child_ids
    FROM macrostrat.projects_tree pt
    WHERE pt.parent_id = ANY(current_ids);
    current_ids := child_ids;
  END LOOP;
  RETURN ARRAY(SELECT DISTINCT unnest(result_ids));
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION macrostrat.core_project_ids() RETURNS integer[] AS $$
SELECT macrostrat.flattened_project_ids(ARRAY[id]) FROM macrostrat.projects WHERE slug = 'core';
$$ LANGUAGE sql STABLE;
