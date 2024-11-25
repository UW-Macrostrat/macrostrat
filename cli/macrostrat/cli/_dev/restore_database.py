import asyncio
from pathlib import Path

from macrostrat.database.transfer import pg_restore_from_file
from macrostrat.utils import get_logger
from rich.console import Console
from sqlalchemy.engine import Engine

console = Console()

log = get_logger(__name__)


def pg_restore(dumpfile: Path, engine: Engine, **kwargs):
    task = pg_restore_from_file(dumpfile, engine, **kwargs)
    asyncio.run(task)
