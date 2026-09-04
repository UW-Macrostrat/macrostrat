from os import environ
from pathlib import Path
from sys import exit

from click.utils import get_app_dir
from dynaconf import Dynaconf
from rich.console import Console
from typer import Context, Option

from macrostrat.app_frame import Application, ControlCommand, DockerComposeManager
from macrostrat.utils import get_logger

from .console import console_theme
from .exc import MacrostratError
from .utils import (
    env_text,
    extract_env_from_argv,
    get_app_state,
    get_app_state_file,
    set_app_state,
)

log = get_logger(__name__)


def load_settings(console: Console):
    try:
        from .config import settings
    except AttributeError as err:
        set_app_state("active_env", None, wipe_others=True)
        raise MacrostratError(
            f"Could not load settings for {env_text()}",
            details="Removing environment configuration",
        )
    except Exception as err:
        # Fake it till we make it with error handling
        console.print_exception(show_locals=False)
        exit(1)

    return settings


class StateManager:
    def get(self, key: str = None) -> str:
        return get_app_state(key)

    def set(self, key: str, value: str, wipe_others: bool = False):
        set_app_state(key, value, wipe_others=wipe_others)

    def clear(self):
        state_file = get_app_state_file()
        if state_file.exists():
            state_file.unlink()


class MacrostratControlCommand(ControlCommand):
    def callback(
        self,
        ctx: Context,
        verbose: bool = Option(False, "--verbose", help="Enable verbose output"),
        # Declared only so `--env` appears in the help text. It is already gone
        # from argv by now — `extract_env_from_argv` consumed it before config
        # loaded — so this parameter is always None and assigning from it here
        # would be a second, later-losing source of truth.
        env: str = Option(None, "--env", "-e", help="Set the active environment"),
    ):
        """:app_name: command-line interface"""
        super().callback(ctx, verbose=verbose)


class Macrostrat(Application):
    settings: Dynaconf
    console: Console
    state: StateManager

    def __init__(self):

        # `--env` has to be read before Typer parses anything, because config
        # is loaded while this object is constructed. One parser, in utils.
        if (env := extract_env_from_argv()) is not None:
            environ["MACROSTRAT_ENV"] = env

        self.console = Console(theme=console_theme)
        self.settings = load_settings(self.console)
        self.state = StateManager()

        # Modules to log when the --verbose flag is set.
        # This is set to macrostrat.* by default, but can be overridden in the config file.
        # For example, you might want to log SQLAlchemy sql queries, in which case you could set this to "macrostrat.*,sqlalchemy.engine".
        log_modules = self.settings.get("log_modules")
        # HACK: we need to actually load each log module here to ensure the loggers are initialized.
        for module in log_modules:
            get_logger(module)

        super().__init__(
            "Macrostrat",
            project_prefix=self.settings.project_name,
            log_modules=log_modules,
        )

    def create_docker_compose_extension(self):
        # TODO: move docker-compose to separate setting
        if self.settings.get("compose_root", None) is None:
            raise MacrostratError("Compose root not set")

        compose_files = []

        root_dir = Path(self.settings.compose_root).expanduser().resolve()
        compose_file = root_dir / "docker-compose.yaml"
        env_file = root_dir / ".env"
        compose_files.append(compose_file)

        mgr = DockerComposeManager(
            self,
            root_dir=root_dir,
            compose_files=compose_files,
            restart_commands={"gateway": "caddy reload --config /etc/caddy/Caddyfile"},
        )

        if env_file.exists(follow_symlinks=True):
            self.load_dotenv(env_file)

        # Add the manager to the control command
        return mgr

    @property
    def app_dir(self):
        return Path(get_app_dir("macrostrat"))

    def control_command(self, *args, **kwargs):
        backend = kwargs.pop("backend")
        cmd = MacrostratControlCommand(self, *args, **kwargs)
        # Hack for local docker compose management
        log.debug("Backend: %s" % backend)
        if backend == "docker-compose":
            mgr = self.create_docker_compose_extension()
            mgr.add_commands(cmd)
        return cmd
