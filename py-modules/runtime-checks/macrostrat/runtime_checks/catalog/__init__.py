"""The runtime check catalog: one module per service."""

from . import api_v2, api_v3, postgrest, tiles, web

CATALOG = [
    *web.CHECKS,
    *api_v2.CHECKS,
    *api_v3.CHECKS,
    *postgrest.CHECKS,
    *tiles.CHECKS,
]
