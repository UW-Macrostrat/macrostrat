from pathlib import Path
from subprocess import run
from sys import argv, exit


def run_user_command_if_provided(*script_dirs: list[Path], look_in_path=False):
    """
    This checks for user-defined shell commands that start with "macrostrat-" in the script_dirs
    defined by the application. These can then be run as
    macrostrat <command> <args>.
    """
    # TODO: integrate this more with the main CLI so that subsystems can also receive user commands

    if len(argv) <= 1:
        return
    args = argv[2:]
    cmd_name = "macrostrat-" + argv[1]
    # Check to see if this command can be found anywhere
    pth = None

    for dir in script_dirs:
        candidate_path = dir / cmd_name
        if candidate_path.exists() and candidate_path.is_file():
            pth = candidate_path
            break

    if look_in_path and pth is None:
        res = run(["which", cmd_name], capture_output=True, text=True)
        if res.returncode == 0:
            pth = res.stdout.strip()

    if pth is None:
        return

    # Run the command
    cmd = [pth] + args
    res = run(cmd)
    exit(res.returncode)
