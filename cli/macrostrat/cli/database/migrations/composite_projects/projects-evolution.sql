
ALTER TABLE macrostrat.projects ADD COLUMN IF NOT EXISTS is_composite BOOLEAN DEFAULT FALSE;


CREATE TABLE IF NOT EXISTS macrostrat.project_composite (
  id integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  parent_project_id integer REFERENCES macrostrat.projects(id) ON DELETE CASCADE,
  child_project_id integer REFERENCES macrostrat.projects(id) ON DELETE CASCADE,
  UNIQUE (parent_project_id, child_project_id)
);

-- Ensure that only composite projects can be parent of other projects
CREATE OR REPLACE FUNCTION macrostrat.check_composite_parent()
RETURNS TRIGGER AS $$
BEGIN
  IF NOT (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.parent_project_id) THEN
    RAISE EXCEPTION 'Parent project must be a composite project';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger on the project_composite table
CREATE TRIGGER trg_check_composite_parent
BEFORE INSERT OR UPDATE ON macrostrat.project_composite
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


/** Take the opportunity to add a slug for nicer URLs **/
ALTER TABLE macrostrat.projects ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE;

/** Function to generate slugs from project names **/
CREATE OR REPLACE FUNCTION macrostrat.generate_project_slug()
RETURNS VOID AS $$
DECLARE
  proj RECORD;
  base_slug TEXT;
  unique_slug TEXT;
  suffix INT;
BEGIN
  FOR proj IN SELECT id, name FROM macrostrat.projects WHERE slug IS NULL LOOP
    base_slug := lower(regexp_replace(proj.name, '[^a-zA-Z0-9]+', '-', 'g'));
    unique_slug := base_slug;
    suffix := 1;
    WHILE EXISTS (SELECT 1 FROM macrostrat.projects WHERE slug = unique_slug) LOOP
      suffix := suffix + 1;
      unique_slug := base_slug || '-' || suffix;
    END LOOP;
    UPDATE macrostrat.projects SET slug = unique_slug WHERE id = proj.id;
  END LOOP;
END;
$$ LANGUAGE plpgsql;
