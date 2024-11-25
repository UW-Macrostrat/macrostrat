from macrostrat.database.transfer.utils import _docker_local_run_args, raw_database_url

from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL

console = Console()

log = get_logger(__name__)


def _create_command(
    *command,
    container=None | str,
):
    """Create a command for operating on a database"""
    _args = []
    if container is not None:
        _args = _docker_local_run_args(container)

    for arg in command:
        if isinstance(arg, Engine):
            arg = arg.url
        if isinstance(arg, URL):
            arg = raw_database_url(arg)
        _args.append(arg)
    return _args
