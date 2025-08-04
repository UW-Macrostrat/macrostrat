from typer import Typer

from .upgrade_db import extend_schema, upgrade_db

app = Typer(no_args_is_help=True, short_help="Macrostrat CLI v2 commands")

app.command(name="upgrade-db", deprecated=True)(upgrade_db)
app.command(name="extend-schema", deprecated=True)(extend_schema)
