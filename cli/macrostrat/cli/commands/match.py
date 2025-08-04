import sys

from . import match_scripts
from .base import Base


class Match(Base):
    """
    macrostrat match <script> <source_id>:
        Scripts for matching geologic maps to columns

    Available scripts:
        strat_names
        units
        liths
        fossils_strat_names
    Usage:
      macrostrat match <script> <source_id>
      macrostrat match -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat match strat_names 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    def run(self):
        # Check if a table was provided
        if len(self.args) != 3 and self.args[1] != "fossils_strat_names":
            print("Wrong number of arguments")
            sys.exit()

        # Validate the passed script
        cmd = self.args[1]
        if cmd not in dir(match_scripts) and cmd != "all":
            print("Invalid script")
            sys.exit()

        script = getattr(match_scripts, cmd)

        if (len(self.args) - 2) != len(script.meta["required_args"]) or (
            len(self.args) == 2 and self.args[1] != "fossils_strat_names"
        ):
            print(
                "You are missing a required argument for this command. The following arguments are required:"
            )
            for arg in script.meta["required_args"]:
                print("     + %s - %s" % (arg, script.meta["required_args"][arg]))
            sys.exit()

        script = script(
            {
                "pg": self.pg["raw_connection"],
                "mariadb": self.mariadb["raw_connection"],
                "credentials": self.credentials,
            },
            self.args[2:],
        )

        if self.args[1] == "fossils_strat_names":
            script.run("foo")
        else:
            script.run(self.args[2])
