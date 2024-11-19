from .strabospot import app as strabospot_app

cli_apps = {
    "strabospot": strabospot_app,
}


def register_migrations():
    from .strabospot.schema import StrabospotBaseSchema
