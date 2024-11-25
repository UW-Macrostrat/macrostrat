import asyncio

from macrostrat.database.transfer import move_tables
from macrostrat.utils import get_logger

log = get_logger(__name__)


def transfer_tables(*args, **kwargs):
    """Transfer tables from one database to another."""
    asyncio.run(move_tables(*args, **kwargs))
