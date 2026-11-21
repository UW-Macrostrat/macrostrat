---
api-v3: minor
---

- `/usage-stats/tiles/requests` adds `presumed_bot`: the overage above the long-term trend during phases of anomalous traffic, recomputed over the whole archive on each read
- `/usage-stats/tiles/throttled` lists the clients the tile cache refused
- `/usage-stats/tiles/maps` returns source ids only, since they are production ids in every environment
