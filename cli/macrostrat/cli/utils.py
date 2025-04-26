from subprocess import run
from sys import argv, exit


def run_user_command_if_provided():
    # Run a user command if it's on the path.
    # Before we do anything else, we want to check if we're working with a command on the path
    # that starts with "macrostrat-". If so, we want to run it as a subprocess.

    # TODO: integrate this more with the main CLI so that subsystems can also receive user commands

    if len(argv) <= 1:
        return
    args = argv[1:]
    cmd_name = "macrostrat-" + argv[1]
    # Check to see if this command can be found anywhere on the path
    pth = run(["which", cmd_name])
    if pth.returncode == 0:
        res = run([cmd_name, *args], check=True)
        exit(res.returncode)
