from os import environ
from pathlib import Path
from sys import exit

import toml
from dynaconf import Dynaconf
from macrostrat.app_frame import Application, Subsystem, SubsystemManager
from macrostrat.app_frame.control_command import OrderCommands
from macrostrat.utils import get_logger
from rich.console import Console
from typer import Typer, get_app_dir

from .console import console_theme
from .exc import MacrostratError

log = get_logger(__name__)


def get_app_state_file() -> Path:
    APP_NAME = "macrostrat"
    app_dir = Path(get_app_dir(APP_NAME))
    return app_dir / "app-state.toml"


def get_app_state(key: str = None) -> str:
    state_file = get_app_state_file()
    if not state_file.exists():
        return None
    with state_file.open() as f:
        state = toml.load(f)
    if key is None:
        return state
    return state.get(key, None)


def set_app_state(key: str, value: str, wipe_others: bool = False):
    state_file = get_app_state_file()
    state_file.parent.mkdir(exist_ok=True)
    state = get_app_state()
    if state is None or wipe_others:
        state = {}
    state[key] = value
    with state_file.open("w") as f:
        toml.dump(state, f)


def load_settings(console: Console):
    if "MACROSTAT_ENV" in environ:
        log.info("active environment: %s", env_text())
    active_env = get_app_state_file()
    if "MACROSTRAT_ENV" not in environ and active_env.exists():
        env = get_app_state("active_env")
        if env is not None:
            environ["MACROSTRAT_ENV"] = env
        log.info("active environment: %s", env_text())

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


class MacrostratSubsystem(Subsystem):
    def __init__(self, app: Application):
        self.app = app
        self.settings = app.settings

    def control_command(self, **kwargs):
        return Typer(no_args_is_help=True, cls=OrderCommands, **kwargs)


class StateManager:
    def get(self, key: str = None) -> str:
        return get_app_state(key)

    def set(self, key: str, value: str, wipe_others: bool = False):
        set_app_state(key, value, wipe_others=wipe_others)


class Macrostrat(Application):
    subsystems: SubsystemManager
    settings: Dynaconf
    console: Console
    state: StateManager

    def __init__(self, *args, **kwargs):
        self.console = Console(theme=console_theme)
        self.settings = load_settings(self.console)
        self.subsystems = SubsystemManager()
        self.state = StateManager()

        compose_files = []
        env_file = None
        root_dir = None
        if self.settings.get("compose_root", None) is not None:
            root_dir = Path(self.settings.compose_root).expanduser().resolve()
            compose_file = root_dir / "docker-compose.yaml"
            env_file = root_dir / ".env"
            compose_files.append(compose_file)

        super().__init__(
            "Macrostrat",
            root_dir=root_dir,
            project_prefix=self.settings.project_name,
            log_modules=["macrostrat"],
            compose_files=compose_files,
            load_dotenv=env_file,
            # This only applies to Docker Compose
            restart_commands={"gateway": "caddy reload --config /etc/caddy/Caddyfile"},
        )

        # Remove DOCKER_BUILDKIT=1 from the environment if we are in offline mode
        # This should possible be merged in upstream
        if self.settings.offline:
            cfg = environ["DOCKER_BUILDKIT"] = "0"
            log.info("Disabling Docker BuildKit for offline mode")

        self.subsystems._app = self

    def finish_loading_subsystems(self):
        self.subsystems.finalize(self)

    @property
    def app_dir(self):
        return Path(get_app_dir("macrostrat"))


def env_text():
    return f"environment [bold cyan]{environ.get('MACROSTRAT_ENV')}[/]"
