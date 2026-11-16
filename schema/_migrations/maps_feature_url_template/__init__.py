from macrostrat.schema_management import Migration, has_columns


class MapsFeatureUrlTemplateMigration(Migration):
    name = "maps-feature-url-template"
    subsystem = "maps"
    description = """
    Add maps.sources.feature_url_template, a link to each feature's own record
    at its publisher, built by substituting the feature's orig_id.
    """
    depends_on = ["baseline"]
    readiness_state = "ga"

    postconditions = [has_columns("maps", "sources", "feature_url_template")]
