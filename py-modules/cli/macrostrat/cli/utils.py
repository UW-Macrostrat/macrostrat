from pathlib import Path
from subprocess import run
from sys import argv, exit
import os
from macrostrat.utils import get_logger

log = get_logger(__name__)


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


def activate_proxy(app):
    """Activate a proxy if environment variables are set or provided by a command"""
    settings = app.settings
    proxy_command = None
    if settings.proxy_command is not None:
        proxy_command = settings.proxy_command
        log.info(f"Running proxy command: {proxy_command}")
        output = run(proxy_command.split(), capture_output=True, text=True)
        load_env_vars(output.stdout)

    # Set up proxy based on variables
    proxy_address = None
    if "http_proxy" in os.environ:
        proxy_address = os.environ["http_proxy"]
    if "https_proxy" in os.environ:
        proxy_address = os.environ["https_proxy"]
    if "HTTP_PROXY" in os.environ:
        proxy_address = os.environ["HTTP_PROXY"]
    if "HTTPS_PROXY" in os.environ:
        proxy_address = os.environ["HTTPS_PROXY"]

    if settings.proxy_address is not None:
        proxy_address = settings.proxy_address

    if proxy_address is None:
        if proxy_command is not None:
            warning = f"Proxy command [cyan]{proxy_command}[/cyan] did not set a proxy address"
            log.warning(warning)
            app.warnings.append(warning)
        return

    import socket
    import socks

    # Set up a SOCKS proxy for all connections
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, proxy_address)
    socket.socket = socks.socksocket
    app.info.append(f"Using SOCKS5 proxy: [cyan]{proxy_address}[/cyan]")


def load_env_vars(output: str):
    """Find and parse environment variable definitions from a command output and set them in the current environment"""
    for line in output.splitlines():
        if line.startswith("export"):
            key, value = line.split("=", 1)
            key = key.replace("export ", "")
            value = value.strip()
            # Handle quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            log.debug(f"Loaded environment variable: {key}={value}")
            os.environ[key] = value
