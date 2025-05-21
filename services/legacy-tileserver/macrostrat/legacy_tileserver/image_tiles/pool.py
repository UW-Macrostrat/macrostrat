import time
from contextlib import contextmanager
from queue import Queue

from macrostrat.database import Database
from macrostrat.utils import get_logger
from mapnik import Map, load_map_from_string, Image, render, Box2d

from .config import scales
from .mapnik_styles import make_mapnik_xml

log = get_logger(__name__)


class MapnikMapPool:
    """A simple, lazy queue-based object pool of Mapnik maps for rendering tiles."""

    storage: dict[str, Queue[Map]] = {}
    n_instances: int = 4

    def __init__(self, db: Database, n_instances: int = 4):
        self.n_instances = n_instances
        for scale in scales:
            self.storage[scale] = self.setup_queue(db, scale)

    def setup_queue(self, db: Database, scale: str):
        """Set up the queue for a given scale."""
        q = Queue(self.n_instances)
        # Fill the queue with Mapnik maps
        t = time.time()
        _xml = make_mapnik_xml(scale, db.engine.url)
        log.info(f"Generated mapnik XML for scale {scale} in {time.time() - t} seconds")
        for _ in range(self.n_instances):
            _map = Map(512, 512)
            load_map_from_string(_map, _xml)
            q.put(_map)
        return q

    @contextmanager
    def map_context(self, scale: str) -> Map:
        """Get a map from the pool."""
        q = self.storage[scale]
        _map = q.get()
        try:
            yield _map
        finally:
            q.put(_map)
