import time
from asyncio import Queue
from contextlib import asynccontextmanager

from mapnik import Map, load_map_from_string

from macrostrat.database import Database
from macrostrat.utils import get_logger

from .config import scales
from .mapnik_styles import make_mapnik_xml

log = get_logger(__name__)


class MapnikMapPool:
    """A simple, lazy queue-based object pool of Mapnik maps for rendering tiles."""

    storage: dict[str, Queue[Map, None]] = {}
    n_instances: int = 4

    def __init__(self, n_instances: int = 4):
        self.n_instances = n_instances

    async def setup(self, db: Database):
        for scale in scales:
            self.storage[scale] = await self.setup_queue(db, scale)

    async def setup_queue(self, db: Database, scale: str):
        """Set up the queue for a given scale."""
        q = Queue(self.n_instances)
        # Fill the queue with Mapnik maps
        t = time.time()
        _xml = make_mapnik_xml(scale, db.engine.url)
        log.info(f"Generated mapnik XML for scale {scale} in {time.time() - t} seconds")
        for _ in range(self.n_instances):
            _map = Map(512, 512)
            load_map_from_string(_map, _xml)
            await q.put(_map)
        return q

    @asynccontextmanager
    async def map_context(self, scale: str) -> Map:
        """Get a map from the pool."""
        q = self.storage[scale]
        _map = await q.get()
        try:
            yield _map
        finally:
            await q.put(_map)
