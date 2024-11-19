from typer import Typer


app = Typer(no_args_is_help=True)


def register_migrations():
    from .strabospot.schema import StrabospotBaseSchema
