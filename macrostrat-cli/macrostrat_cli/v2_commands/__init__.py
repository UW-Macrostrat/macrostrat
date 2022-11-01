from typer import Typer

from .upgrade_db import upgrade_db, extend_schema


app = Typer(no_args_is_help=True)

app.command(name="upgrade-db")(upgrade_db)
app.command(name="extend-schema")(extend_schema)
