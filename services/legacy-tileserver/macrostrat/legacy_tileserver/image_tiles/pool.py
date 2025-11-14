from asyncio import Queue

import time
from contextlib import asynccontextmanager
from macrostrat.database import Database
from macrostrat.utils import get_logger
from mapnik import Map, load_map_from_string

from .config import scales
from .mapnik_styles import (
    make_mapnik_xml,
    make_line_datasource,
    make_polygon_datasource,
)

log = get_logger(__name__)


class MapnikMapPool:
    """A simple, lazy queue-based object pool of Mapnik maps for rendering tiles."""

    storage: dict[str, Queue[Map, None]] = {}
    n_instances: int = 4

    line_datasources: dict[str, object] = {}
    polygon_datasources: dict[str, object] = {}

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

        # Set up PostGIS data sources for shared use here

        line_datasource = make_line_datasource(db.engine.url, scale)
        polygon_datasource = make_polygon_datasource(db.engine.url, scale)

        self.line_datasources[scale] = line_datasource
        self.polygon_datasources[scale] = polygon_datasource

        log.info(f"Generated mapnik XML for scale {scale} in {time.time() - t} seconds")
        for _ in range(self.n_instances):
            _map = Map(512, 512)
            load_map_from_string(_map, _xml)
            # Set up shared data sources here
            for layer in _map.layers:
                if layer.name == f"lines_{scale}":
                    layer.datasource = line_datasource
                elif layer.name == f"units_{scale}":
                    layer.datasource = polygon_datasource
            await q.put(_map)
            dt = time.time() - t
        log.info(
            f"Initialized {self.n_instances} map objects for scale {scale} in {dt} seconds"
        )
        return q

    @asynccontextmanager
    async def map_context(self, scale: str) -> Map:
        """Get a map from the pool."""
        q = self.storage[scale]
        _map = await q.get()
        t = time.time()
        try:
            yield _map
        finally:
            await q.put(_map)
            dt = time.time() - t
            log.debug(f"Returned map to pool for scale {scale} in {dt:.3f} seconds")
