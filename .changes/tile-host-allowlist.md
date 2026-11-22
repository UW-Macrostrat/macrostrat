---
api-gateway: minor
---

- The tile host serves only the tileserver's routes, so it keeps its scope once tiles are served by API v3; other paths get a 404 pointing to `/api/v3`
- Cache-management paths on the tile host answer 404 rather than 403
