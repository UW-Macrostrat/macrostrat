from os import environ
from pathlib import Path
from sys import exit
from typing import Any

from click.utils import get_app_dir
from rich.console import Console
from typer import Context, Option

from macrostrat.app_frame import Application, ControlCommand, DockerComposeManager
from macrostrat.utils import get_logger

from .console import console_theme
from .exc import ConfigError, MacrostratError, UnknownEnvironment
from .utils import (
    ENV_EXPIRES_VAR,
    ENV_VAR,
    extract_env_from_argv,
    get_app_state,
    get_app_state_file,
    set_app_state,
)

log = get_logger(__name__)


#: Top-level command groups that inspect or change the environment rather than
#: use it. A lapsed environment is not questioned on the way into these — the
#: point of `macrostrat env` is to fix exactly that situation.
ENVIRONMENT_NEUTRAL_COMMANDS = frozenset({"env", "config", "self", "install", "uv"})


def load_settings(console: Console):
    try:
        from .config import settings
    except (UnknownEnvironment, ConfigError) as err:
        # Raised during config load, before Click is running, so nothing else
        # will render it. Say what was wrong and stop.
        console.print(f"[bold red]Error:[/] {err.message}")
        if err.details:
            console.print(err.details)
        exit(1)
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
        # A remembered environment that has lapsed is kept, and questioned
        # here — once, before any command that could use it. Click has already
        # handled --help by this point, and a bare `macrostrat` invokes no
        # subcommand, so neither ever prompts.
        if ctx.invoked_subcommand not in ENVIRONMENT_NEUTRAL_COMMANDS | {None}:
            from .safety import require_environment

            require_environment(settings=self.app.settings)

        # The compose stack needs its credentials in plaintext at start time.
        # A vaulted config withholds them from the ambient environment, so
        # they are resolved here, for the compose commands only, once the
        # environment has been confirmed above.
        from .compose_env import COMPOSE_COMMANDS, export_compose_environment

        if (
            ctx.invoked_subcommand in COMPOSE_COMMANDS
            and self.app.settings.backend == "docker-compose"
        ):
            export_compose_environment(self.app.settings)


class Macrostrat(Application):
    settings: Any
    console: Console
    state: StateManager

    def __init__(self):
        # `--env` has to be read before Typer parses anything, because config
        # is loaded while this object is constructed. One parser, in utils.
        if (env := extract_env_from_argv()) is not None:
            environ[ENV_VAR] = env
            # Explicit beats a shell session's expiry: --env is per-invocation.
            environ.pop(ENV_EXPIRES_VAR, None)

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
            restart_commands={
                "gateway": "caddy reload --config /etc/caddy/Caddyfile",
                # Varnish resolves its backends' hostnames once, when the VCL is
                # loaded. A recreated tileserver_core therefore leaves the cache
                # dialing a stale container IP, and every core-backed tile route
                # 503s until varnish itself is restarted. Reloading the VCL
                # re-resolves the backends (and picks up edits to
                # configs/tileserver-cache.vcl) without dropping cached objects.
                "tileserver_cache": "varnishreload",
            },
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
