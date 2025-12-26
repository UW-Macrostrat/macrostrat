DO $$
DECLARE
  _core_project_id integer;
BEGIN

INSERT INTO macrostrat.projects (project, descrip, timescale_id, is_composite, slug)
VALUES
  ('Core columns',
   'A composite dataset containing a non-overlapping set of regional composite columns at regional scale.',
   1,
   TRUE,
   'core')
ON CONFLICT (slug) DO NOTHING
RETURNING id INTO _core_project_id;

INSERT INTO macrostrat.projects_tree (parent_id, child_id)
SELECT _core_project_id, id
FROM macrostrat.projects p
WHERE p.slug IN ('north-america', 'caribbean', 'south-america', 'africa', 'eodp');

END;
$$ LANGUAGE plpgsql;
