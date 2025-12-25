from macrostrat.core.migrations import Migration, _not, exists, has_columns


def check_slug_not_nullable(db):
    result = db.run_query(
        """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'macrostrat'
          AND table_name = 'project'
          AND column_name = 'slug';
        """
    ).one_or_none()
    if result is None:
        return False
    return result.is_nullable


success = [
    has_columns("macrostrat", "project", "is_composite", "slug"),
    exists("macrostrat", "projects_tree"),
    # Slug is not nullable
    check_slug_not_nullable,
]


class CompositeProjects(Migration):
    name = "composite-projects"
    subsystem = "columns"
    description = "Composite projects support"
    preconditions = [_not(a) for a in success]
    postconditions = success
