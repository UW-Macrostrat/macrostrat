from typer import Typer
import sys
from .commands.ingest import ingest_map


class IngestionCLI(Typer):
    def add_command(self, func, **kwargs):
        self.command(**kwargs)(func)


app = IngestionCLI(no_args_is_help=True, add_completion=False)
app.command(name="ingest")(ingest_map)


@app.command(name="test")
def test():
    print("test")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "map":
        sys.argv = sys.argv[1:]
        app()
    else:
        # Fall back to rest of CLI if we're not dealing with maps
        # NOTE: this should probably be inverted eventually.
        # The map CLI should be a subcommand of the main CLI,
        # not the other way around.
        try:
            from macrostrat_cli.cli import main

            main()
        except ModuleNotFoundError:
            print("macrostrat's main CLI is not installed")
            return
