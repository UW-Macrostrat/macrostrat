DO $$
DECLARE
  _core_project_id integer;
BEGIN

INSERT INTO macrostrat.projects (id, project, descrip, timescale_id, is_composite, slug)
VALUES
  (
   14,
   'Core columns',
   'The "best available" default set of regional columns, composited from other datasets.',
   1,
   TRUE,
   'core'
  )
ON CONFLICT (id) DO NOTHING;

SELECT id INTO _core_project_id
FROM macrostrat.projects
WHERE slug = 'core';

INSERT INTO macrostrat.projects_tree (parent_id, child_id)
SELECT _core_project_id, id
FROM macrostrat.projects p
WHERE p.slug IN ('north-america', 'caribbean', 'south-america', 'africa', 'eodp')
ON CONFLICT DO NOTHING;

END;
$$ LANGUAGE plpgsql;
