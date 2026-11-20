---
api-gateway: minor
---

- Tile cache answers 429 to clients over a per-client render limit; `TILE_THROTTLE_MODE=report` only marks them (`X-Throttle: would-deny`)
