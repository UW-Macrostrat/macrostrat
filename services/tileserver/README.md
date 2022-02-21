# The v2 tile server for Macrostrat

- Python-based instead of Node-based
- Uses Mapnik for legacy image-tile generation
- Uses a PostgreSQL caching backend (this is the primary simplification)
- Uses Varnish for caching API results