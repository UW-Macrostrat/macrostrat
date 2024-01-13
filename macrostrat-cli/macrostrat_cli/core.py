from macrostrat.app_frame import Application, SubsystemManager
from pathlib import Path
from os import environ
from sys import stderr
from rich import print
from typer import get_app_dir
from dynaconf import Dynaconf


def load_settings():
    APP_NAME = "macrostrat"
    app_dir = Path(get_app_dir(APP_NAME))
    active_env = app_dir / "~active_env"
    if "MACROSTAT_ENV" in environ:
        print(f"Using {env_text()}", file=stderr)
    if "MACROSTRAT_ENV" not in environ and active_env.exists():
        environ["MACROSTRAT_ENV"] = active_env.read_text().strip()
        user_dir = str(Path("~").expanduser())
        dir = str(active_env).replace(user_dir, "~")
        print(
            f"Using {env_text()}\n[dim] from {dir}[/]",
            file=stderr,
        )

    try:
        from .config import settings
    except AttributeError as err:
        print(f"Could not load settings for {env_text()}", file=stderr)
        print(err, file=stderr)
        print("Removing environment configuration", file=stderr)
        active_env.unlink()
        exit(1)

    return settings


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
            app_module="macrostrat_cli",
            compose_files=compose_files,
            load_dotenv=env_file,
            # This only applies to Docker Compose
            restart_commands={"gateway": "nginx -s reload"},
        )

        self.subsystems._app = self


def env_text():
    return f"environment [bold cyan]{environ.get('MACROSTRAT_ENV')}[/]"


app = Macrostrat()
