from typer import Typer, Argument
from pathlib import Path
import sys

from .upgrade_db import upgrade_db, extend_schema

app = Typer(no_args_is_help=True, short_help="Macrostrat CLI v2 commands")

app.command(name="upgrade-db")(upgrade_db)
app.command(name="extend-schema")(extend_schema)

@app.command(name="play")
def play(playbook: str = Argument(None)):
    """Run ansible playbooks."""
    from ansible.cli.playbook import main
    sys.argv = ["ansible-playbook"]
    if playbook is None:
        # List all playbooks
        print("Available playbooks:")
        for playbook in Path("/data/macrostrat").glob("ansible/playbooks/*.yaml"):
            print (f"  {playbook}")
        return

    if playbook is not None:
        play_file = Path("/data/macrostrat")/"ansible"/"playbooks"/(playbook+".yaml")
        if not play_file.exists():
            raise Exception(f"Playbook {playbook} not found")
        sys.argv.append(str(play_file))
    main()
