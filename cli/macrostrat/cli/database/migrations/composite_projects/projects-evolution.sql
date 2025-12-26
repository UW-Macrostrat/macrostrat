ALTER SCHEMA macrostrat OWNER TO macrostrat;

DROP VIEW IF EXISTS macrostrat_api.projects;
DROP VIEW IF EXISTS macrostrat_api.col_group_with_cols;

-- Alter project name to text
ALTER TABLE macrostrat.projects ALTER COLUMN project TYPE TEXT USING project::TEXT;

-- drop custom type
DROP TYPE IF EXISTS macrostrat.projects_project;


ALTER TABLE macrostrat.projects ADD COLUMN IF NOT EXISTS is_composite BOOLEAN DEFAULT FALSE;
/** Take the opportunity to add a slug for nicer URLs **/
ALTER TABLE macrostrat.projects ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE;

CREATE TABLE IF NOT EXISTS macrostrat.projects_tree (
  id integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  parent_id integer NOT NULL REFERENCES macrostrat.projects(id) ON DELETE CASCADE,
  child_id integer NOT NULL REFERENCES macrostrat.projects(id) ON DELETE CASCADE,
  UNIQUE (parent_id, child_id)
);
ALTER TABLE macrostrat.projects_tree OWNER TO macrostrat;

-- Ensure that only composite projects can be parent of other projects
CREATE OR REPLACE FUNCTION macrostrat.check_composite_parent()
RETURNS TRIGGER AS $$
BEGIN
  IF NOT (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.parent_id) THEN
    RAISE EXCEPTION 'Parent project must be a composite project';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger on the project_composite table
CREATE TRIGGER trg_check_composite_parent
BEFORE INSERT OR UPDATE ON macrostrat.projects_tree
FOR EACH ROW EXECUTE FUNCTION macrostrat.check_composite_parent();

/**
  Ensure that only non-composite projects can have columns as children.
  This is probably not strictly necessary, but it makes the composite project
  system a bit more straightforward at the start.
*/
CREATE OR REPLACE FUNCTION macrostrat.check_column_project_non_composite()
RETURNS TRIGGER AS $$
BEGIN
  IF (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.project_id)
  THEN
    RAISE EXCEPTION 'A composite project cannot itself contain columns. We may relax this restriction in the future.';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add the trigger on the macrostrat.cols table
CREATE TRIGGER trg_check_column_project_non_composite
BEFORE INSERT OR UPDATE ON macrostrat.cols
FOR EACH ROW EXECUTE FUNCTION macrostrat.check_column_project_non_composite();

DROP FUNCTION IF EXISTS macrostrat.generate_project_slug(macrostrat.projects);
CREATE OR REPLACE FUNCTION macrostrat.generate_project_slug(_project macrostrat.projects)
RETURNS TEXT AS $$
DECLARE
  base_slug TEXT;
  unique_slug TEXT;
  suffix INT;
BEGIN
  base_slug := lower(regexp_replace(_project.project, '[^a-zA-Z0-9]+', '-', 'g'));
  unique_slug := base_slug;
  suffix := 1;
  WHILE EXISTS (SELECT 1 FROM macrostrat.projects p WHERE p.slug = unique_slug AND p.id != _project.id) LOOP
    suffix := suffix + 1;
    unique_slug := base_slug || '-' || suffix;
  END LOOP;
  RETURN unique_slug;
END;
$$ LANGUAGE plpgsql;

/** Generate slugs from existing projects **/
UPDATE macrostrat.projects p
SET slug = macrostrat.generate_project_slug(p)
WHERE slug IS NULL;

-- Set slug column to NOT NULL
ALTER TABLE macrostrat.projects ALTER COLUMN slug SET NOT NULL;


-- Create an index on the slug column for faster lookups
CREATE INDEX IF NOT EXISTS idx_projects_slug ON macrostrat.projects(slug);

