from os import environ
from pathlib import Path
from sys import stderr

from dynaconf import Dynaconf
from macrostrat.app_frame import Application, Subsystem, SubsystemManager
from macrostrat.utils import get_logger
from rich import print
from typer import Typer, get_app_dir

log = get_logger(__name__)


def get_app_env_file() -> Path:
    APP_NAME = "macrostrat"
    app_dir = Path(get_app_dir(APP_NAME))
    return app_dir / "~active_env"


def load_settings():
    active_env = get_app_env_file()
    if "MACROSTAT_ENV" in environ:
        log.info("active environment: %s", env_text())
    if "MACROSTRAT_ENV" not in environ and active_env.exists():
        environ["MACROSTRAT_ENV"] = active_env.read_text().strip()
        user_dir = str(Path("~").expanduser())
        dir = str(active_env).replace(user_dir, "~")
        log.info("active environment: %s", env_text())

    try:
        from .config import settings
    except AttributeError as err:
        print(f"Could not load settings for {env_text()}", file=stderr)
        print(err, file=stderr)
        print("Removing environment configuration", file=stderr)
        active_env.unlink()
        exit(1)

    return settings


class MacrostratSubsystem(Subsystem):
    def __init__(self, app: Application):
        self.app = app
        self.settings = app.settings

    def control_command(self, **kwargs):
        return Typer(no_args_is_help=True, **kwargs)


class Macrostrat(Application):
    subsystems: SubsystemManager
    settings: Dynaconf

    def __init__(self, *args, **kwargs):
        self.settings = load_settings()
        self.subsystems = SubsystemManager()

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
            app_module="macrostrat",
            compose_files=compose_files,
            load_dotenv=env_file,
            # This only applies to Docker Compose
            restart_commands={"gateway": "nginx -s reload"},
        )

        self.subsystems._app = self


def env_text():
    return f"environment [bold cyan]{environ.get('MACROSTRAT_ENV')}[/]"
