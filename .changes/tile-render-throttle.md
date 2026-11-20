---
api-gateway: minor
---

- Tile cache marks clients over a render limit with `X-Throttle: would-deny` (report-only; 429 enforcement is commented out in `tiles.vcl`)
